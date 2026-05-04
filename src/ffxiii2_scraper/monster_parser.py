from pathlib import Path
import json
import re
import shutil
import unicodedata

from bs4 import BeautifulSoup

from .paths import PARSED_MONSTERS_DIR, RAW_HTML_DIR, ensure_project_dirs


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def clean_prose(value: str | None) -> str | None:
    value = clean_text(value)
    if value is None:
        return None
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"\(\s+", "(", value)
    value = re.sub(r"\s+\)", ")", value)
    value = re.sub(r"(\w)\s+'(\w)", r"\1'\2", value)
    return value


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def parse_number(value: str | None) -> int | float | None:
    if not value:
        return None
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None
    number_str = match.group(0)
    if "." in number_str:
        return float(number_str)
    return int(number_str)


def parse_monster_image(soup: BeautifulSoup) -> str | None:
    img = soup.select_one('figure.pi-image[data-source="image"] img')
    if not img:
        img = soup.select_one("figure img")
    if not img:
        return None

    src = img.get("src")
    data_src = img.get("data-src")
    if src and not src.startswith("data:image/"):
        return src
    if data_src:
        return data_src
    return src


def is_disambiguation_page(soup: BeautifulSoup) -> bool:
    if soup.select_one(".disambig"):
        return True
    first_paragraph = soup.select_one(".mw-parser-output > p")
    if first_paragraph:
        text = clean_text(first_paragraph.get_text(" ", strip=True)) or ""
        if "may refer to:" in text:
            return True
    return False


def get_infobox_value(soup: BeautifulSoup, data_source: str) -> str | None:
    selectors = [
        f'.pi-smart-data-value[data-source="{data_source}"]',
        f'[data-source="{data_source}"] .pi-data-value',
        f'[data-source="{data_source}"] .pi-smart-data-value',
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return clean_text(element.get_text(" ", strip=True))
    return None


def get_title(soup: BeautifulSoup) -> str | None:
    title = soup.select_one(".pi-title")
    if title:
        return clean_text(title.get_text(" ", strip=True))

    h1 = soup.select_one("h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))

    intro_bold = soup.select_one(".mw-parser-output > p > b")
    if intro_bold:
        return clean_text(intro_bold.get_text(" ", strip=True))

    name_value = soup.select_one('[data-source="name"] .pi-data-value')
    if name_value:
        return clean_text(name_value.get_text(" ", strip=True))

    return None


def parse_smart_group_values(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for value_el in soup.select(".pi-smart-data-value[data-source]"):
        key = value_el.get("data-source")
        value = clean_text(value_el.get_text(" ", strip=True))
        if key and value is not None:
            values[key] = value
    return values


def parse_locations(soup: BeautifulSoup) -> list[dict]:
    location_el = soup.select_one('[data-source="location"] .pi-data-value')
    if not location_el:
        return []

    location_html = BeautifulSoup(str(location_el), "lxml")
    for br in location_html.select("br"):
        br.replace_with("||")

    raw_locations = [
        clean_text(part)
        for part in location_html.get_text(" ", strip=True).split("||")
    ]

    return [
        {
            "name": location,
            "slug": slugify(location),
            "source_url": None,
        }
        for location in raw_locations
        if location
    ]


def parse_affinities(smart_values: dict[str, str]) -> dict[str, list[str]]:
    affinity_keys = ["fire", "ice", "lightning", "wind", "physical", "magical"]
    display_names = {
        "fire": "Fire",
        "ice": "Ice",
        "lightning": "Lightning",
        "wind": "Wind",
        "physical": "Physical",
        "magical": "Magical",
    }
    result = {"weak": [], "halved": [], "resistant": [], "immune": []}

    for key in affinity_keys:
        value = smart_values.get(key)
        if not value:
            continue

        pct = parse_int(value)
        name = display_names[key]

        if pct == 0:
            result["immune"].append(name)
        elif pct is not None and pct >= 150:
            result["weak"].append(name)
        elif pct == 50:
            result["halved"].append(name)
        elif pct is not None and pct < 100:
            result["resistant"].append(name)

    return result


def parse_abilities(soup: BeautifulSoup) -> dict:
    abilities = {"passives": [], "skills": []}
    table = soup.select_one("table.article-table")
    if not table:
        return abilities

    for row in table.select("tbody tr"):
        cells = row.select("th, td")
        if len(cells) < 4:
            continue

        name = clean_text(cells[0].get_text(" ", strip=True))
        if not name or name.lower() == "ability":
            continue

        level_str = clean_text(cells[1].get_text(" ", strip=True)) or ""
        type_str = clean_text(cells[2].get_text(" ", strip=True)) or ""
        infuse_cell = cells[3]

        has_check = bool(infuse_cell.select_one(".checkmark"))
        has_xmark = bool(infuse_cell.select_one(".xmark"))
        can_infuse = has_check and not has_xmark

        base_entry = {
            "name": name,
            "slug": slugify(name),
            "source_url": None,
            "level": 1 if level_str.lower() == "initial" else parse_int(level_str),
            "default": level_str.lower() == "initial",
        }

        if type_str == "Passive":
            abilities["passives"].append({**base_entry, "red_locked": not can_infuse})
        else:
            abilities["skills"].append({**base_entry, "infusable": can_infuse})

    return abilities


def parse_paradigm_pack_notes(soup: BeautifulSoup) -> str | None:
    section_marker = soup.select_one('#Paradigm_Pack')
    if not section_marker:
        return None

    heading = section_marker.find_parent(["h2", "h3"])
    if heading is None:
        return None

    paragraphs: list[str] = []
    for sibling in heading.find_next_siblings():
        if getattr(sibling, "name", None) in {"h2", "h3"}:
            break
        if getattr(sibling, "name", None) == "p":
            text = clean_prose(sibling.get_text(" ", strip=True))
            if text:
                paragraphs.append(text)

    if not paragraphs:
        return None

    return "\n\n".join(paragraphs)


def parse_monster(
    html: str,
    source_file: str,
) -> dict:
    soup = BeautifulSoup(html, "lxml")
    smart_values = parse_smart_group_values(soup)

    name = get_title(soup)

    feral_link_raw = get_infobox_value(soup, "feral link")
    feral_link = None
    if feral_link_raw:
        feral_link = {
            "name": feral_link_raw,
            "description": None,
            "type": None,
            "damage_modifier": None,
            "charge_time_seconds": None,
            "effects": [],
            "combos": {"ps3": [], "xbox": []},
        }

    traits = smart_values.get("traits", "") or ""
    traits_lower = traits.lower()
    growth = None
    if "well-grown" in traits_lower or "well grown" in traits_lower:
        growth = "Well-grown"
    elif "early peaker" in traits_lower or "early" in traits_lower:
        growth = "Early Peaker"
    elif "late bloomer" in traits_lower or "late" in traits_lower:
        growth = "Late Bloomer"
    elif "standard" in traits_lower:
        growth = "Standard"

    return {
        "source_url": None,
        "source_id": None,
        "slug": slugify(name) if name else None,
        "name": name,
        "dlc": False,
        "monster_image": parse_monster_image(soup),
        "role": get_infobox_value(soup, "role"),
        "speed": None,
        "tame_rate_pct": parse_number(get_infobox_value(soup, "recruit chance")),
        "max_level": parse_int(smart_values.get("max level")),
        "growth": growth,
        "special_notes": clean_text(traits) if traits else None,
        "paradigm_pack_notes": parse_paradigm_pack_notes(soup),
        "stats": {
            "hp_min": parse_int(smart_values.get("hp")),
            "hp_max": parse_int(smart_values.get("hp")),
            "str_min": parse_int(smart_values.get("strength")),
            "str_max": parse_int(smart_values.get("strength")),
            "mag_min": parse_int(smart_values.get("magic")),
            "mag_max": parse_int(smart_values.get("magic")),
        },
        "feral_link": feral_link,
        "locations": parse_locations(soup),
        "constellations": [],
        "affinities": parse_affinities(smart_values),
        "abilities": parse_abilities(soup),
    }


def parse_all_monsters() -> list[Path]:
    ensure_project_dirs()

    if PARSED_MONSTERS_DIR.exists():
        shutil.rmtree(PARSED_MONSTERS_DIR)
    PARSED_MONSTERS_DIR.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    html_files = [
        path for path in RAW_HTML_DIR.glob("*.html")
        if not path.name.startswith("_INDEX_")
    ]

    print(f"Found {len(html_files)} HTML files")

    for html_file in html_files:
        html = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        if is_disambiguation_page(soup):
            print(f"Skipped disambiguation page: {html_file.name}")
            continue

        monster = parse_monster(html, html_file.name)

        output_path = PARSED_MONSTERS_DIR / f"{monster['slug'] or html_file.stem}.json"
        output_path.write_text(
            json.dumps(monster, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written_files.append(output_path)
        print(f"Parsed: {html_file.name} -> {output_path.name}")

    print("Done.")
    return written_files


def main() -> None:
    parse_all_monsters()
