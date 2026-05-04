from pathlib import Path
import json
import re
import shutil
import unicodedata
from urllib.parse import quote, unquote, urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from .paths import FERAL_LINK_INDEX_FILE, PARSED_FERAL_LINKS_DIR, ensure_project_dirs


BASE_WIKI_URL = "https://finalfantasy.fandom.com"
ROLE_NAMES = {"Commando", "Ravager", "Sentinel", "Saboteur", "Synergist", "Medic"}
INPUT_TYPES = {
    "Single button",
    "Multiple",
    "Timing",
    "Button tap",
    "Stick rotation",
    "Complex",
    "None",
}


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


def resolve_monster_href(link: Tag | None) -> str | None:
    if link is None:
        return None

    href = link.get("href")
    if not href:
        return None

    link_classes = set(link.get("class", []))
    if "mw-disambig" in link_classes:
        display_name = clean_text(link.get_text(" ", strip=True))
        if display_name:
            href = f"/wiki/{quote(display_name.replace(' ', '_') + '_(Final_Fantasy_XIII-2)')}"

    return urljoin(BASE_WIKI_URL, href)


def monster_slug_from_url(url: str | None, fallback_name: str) -> str:
    if not url:
        return slugify(fallback_name)

    path = urlparse(url).path
    title = unquote(path.removeprefix("/wiki/"))
    title = re.sub(r"_\((?:Final_Fantasy_XIII-2|boss|Final_Fantasy_XIII-2_enemy|Final_Fantasy_XIII-2_party_member)\)$", "", title)
    title = title.replace("_", " ")
    return slugify(title) or slugify(fallback_name)


def parse_charge_time_seconds(value: str | None) -> int | None:
    value = clean_text(value)
    if not value:
        return None

    match = re.fullmatch(r"(\d+):(\d{2})", value)
    if not match:
        return None

    minutes = int(match.group(1))
    seconds = int(match.group(2))
    return (minutes * 60) + seconds


def parse_percent(value: str | None) -> int | None:
    value = clean_text(value)
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def infer_feral_link_type(description: str | None) -> str | None:
    description = clean_text(description)
    if not description:
        return None

    lower = description.lower()
    if "restore hp" in lower or "heal" in lower:
        return "Recovery"
    if "enhance" in lower or "bestow" in lower:
        return "Buff"
    if "debilitating" in lower or "debuff" in lower:
        return "Debuff"
    if "magic damage" in lower:
        return "Magic"
    if "physical damage" in lower:
        return "Physical"
    return "Other"


def parse_effect_lines(effect_cell: Tag) -> tuple[str | None, str | None]:
    description = None
    details = None

    italic = effect_cell.select_one("i")
    if italic:
        description = clean_prose(italic.get_text(" ", strip=True))

    cell_html = BeautifulSoup(effect_cell.decode_contents(), "lxml")
    italic_copy = cell_html.select_one("i")
    if italic_copy:
        italic_copy.decompose()

    for br in cell_html.select("br"):
        br.replace_with("\n")

    remaining_text = clean_prose(cell_html.get_text("\n", strip=True))
    if remaining_text:
        detail_lines = [clean_prose(line) for line in remaining_text.splitlines()]
        detail_lines = [line for line in detail_lines if line]
        if detail_lines:
            details = "\n".join(detail_lines)

    return description, details


def parse_effects(effect_cell: Tag) -> list[str]:
    effect_text = clean_text(effect_cell.get_text(" ", strip=True)) or ""
    effect_links: list[str] = []

    for link in effect_cell.select("a"):
        text = clean_text(link.get_text(" ", strip=True))
        if not text:
            continue
        if text in {"target", "allies", "foes"}:
            continue
        if text in effect_links:
            continue
        if text not in effect_text:
            continue
        effect_links.append(text)

    return effect_links


def parse_input_sequences(input_cell: Tag) -> tuple[str, list[str], list[str]]:
    input_type = None
    ps3: list[str] = []
    xbox: list[str] = []
    current_platform = "ps3"
    saw_platform_separator = False

    for child in input_cell.children:
        if isinstance(child, NavigableString):
            text = clean_text(str(child))
            if not text:
                continue
            if text in INPUT_TYPES and input_type is None:
                input_type = text
                continue
            if text == "/":
                current_platform = "xbox"
                saw_platform_separator = True
                continue
            if text.startswith("(") and text.endswith(")"):
                label = text[1:-1].strip()
                if current_platform == "ps3":
                    ps3.append(label)
                else:
                    xbox.append(label)
                continue

        if isinstance(child, Tag):
            if child.name == "br":
                if current_platform == "ps3" and ps3:
                    current_platform = "xbox"
                continue

            for img in child.select("img"):
                alt = clean_text(img.get("alt"))
                if not alt:
                    continue
                if current_platform == "ps3":
                    ps3.append(alt)
                else:
                    xbox.append(alt)

    if not saw_platform_separator and ps3 and not xbox:
        xbox = list(ps3)

    return input_type or "None", ps3, xbox


def parse_feral_link_row(role: str, row: Tag) -> dict | None:
    cells = row.select("th, td")
    if len(cells) != 6:
        return None

    monster_cell, ability_cell, input_cell, effect_cell, cooldown_cell, max_sync_cell = cells

    monster_name = clean_text(monster_cell.get_text(" ", strip=True))
    ability_name = clean_text(ability_cell.get_text(" ", strip=True))
    if not monster_name or not ability_name:
        return None

    monster_link = monster_cell.select_one('a[href^="/wiki/"]')
    monster_url = resolve_monster_href(monster_link)
    monster_slug = monster_slug_from_url(monster_url, monster_name)

    input_type, ps3, xbox = parse_input_sequences(input_cell)
    description, details = parse_effect_lines(effect_cell)

    return {
        "source_url": f"{BASE_WIKI_URL}/wiki/Feral_Link",
        "slug": slugify(ability_name),
        "name": ability_name,
        "role": role,
        "monster": {
            "name": monster_name,
            "slug": monster_slug,
            "source_url": monster_url,
        },
        "input": {
            "type": input_type,
            "ps3": ps3,
            "xbox": xbox,
        },
        "description": description,
        "details": details,
        "type": infer_feral_link_type(description),
        "damage_modifier": None,
        "charge_time_seconds": parse_charge_time_seconds(cooldown_cell.get_text(" ", strip=True)),
        "max_sync_pct": parse_percent(max_sync_cell.get_text(" ", strip=True)),
        "effects": parse_effects(effect_cell),
    }


def parse_feral_links(index_html: str) -> list[dict]:
    soup = BeautifulSoup(index_html, "lxml")
    feral_links: list[dict] = []

    for heading in soup.select("h3"):
        headline = heading.select_one(".mw-headline")
        role = clean_text(headline.get_text(" ", strip=True)) if headline else None
        if role not in ROLE_NAMES:
            continue

        table = heading.find_next_sibling("table")
        if table is None:
            continue

        for row in table.select("tbody tr")[1:]:
            feral_link = parse_feral_link_row(role, row)
            if feral_link is not None:
                feral_links.append(feral_link)

    return feral_links


def parse_all_feral_links() -> list[Path]:
    ensure_project_dirs()

    if PARSED_FERAL_LINKS_DIR.exists():
        shutil.rmtree(PARSED_FERAL_LINKS_DIR)
    PARSED_FERAL_LINKS_DIR.mkdir(parents=True, exist_ok=True)

    if not FERAL_LINK_INDEX_FILE.exists():
        raise FileNotFoundError(f"Could not find {FERAL_LINK_INDEX_FILE}")

    feral_links = parse_feral_links(FERAL_LINK_INDEX_FILE.read_text(encoding="utf-8"))
    written_files: list[Path] = []

    for feral_link in feral_links:
        output_path = PARSED_FERAL_LINKS_DIR / f"{feral_link['monster']['slug']}.json"
        output_path.write_text(
            json.dumps(feral_link, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        written_files.append(output_path)

    print(f"Parsed {len(written_files)} feral links")
    return written_files


def main() -> None:
    parse_all_feral_links()
