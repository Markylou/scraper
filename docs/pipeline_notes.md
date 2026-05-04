1. Define desired final JSON schema
   - What your finished monster object should look like
   - IDs, slugs, normalized fields, references

2. Define raw/intermediate JSON schema
   - Same general data, but using names/slugs instead of IDs
   - Example: "locations": ["Academia 500 AF"] instead of "location_ids": [21]

3. Create URL input list
   - inputs/monster_urls.txt
   - one monster/detail page URL per line
   - later this can be generated from an index page

4. Fetch raw HTML
   - Download each URL
   - Save one HTML file per page
   - Do not parse yet

5. Cache raw HTML locally
   - Example: data/raw_html/apkallu.html
   - This lets you retry extraction without hitting the site again

6. Parse cached HTML
   - Use BeautifulSoup/lxml
   - Extract title, infobox, tables, links, notes, etc.

7. Convert parsed sections into raw structured JSON
   - Use names/text values
   - Do not worry about IDs yet

8. Validate raw JSON shape
   - Required fields exist
   - Correct types
   - Arrays are arrays
   - Numbers are numbers
   - Nullable fields are handled

9. Save raw extracted JSON
   - Example: data/parsed/monsters/apkallu.json

10. Collect discovered entities
   - All unique locations
   - All unique skills
   - All unique passives
   - All unique elements/affinities
   - All unique constellations

11. Build master lookup tables
   - locations.json
   - skills.json
   - passives.json
   - elements.json
   - constellations.json

12. Assign stable IDs
   - Every unique entity gets an ID
   - Keep IDs stable once assigned
   - Do not regenerate IDs randomly every scrape

13. Normalize raw monster JSON
   - Replace names/slugs with IDs
   - Example:
     - "locations": ["Academia 500 AF"]
     - becomes "location_ids": [21]

14. Validate final normalized JSON
   - Final schema validation
   - Referential integrity checks:
     - location_id exists
     - passive_id exists
     - skill_id exists
     - hp_max >= hp_min

15. Save final monster JSON
   - Example: data/final/monsters/apkallu.json

16. Log failures
   - Missing fields
   - Failed parses
   - Unknown references
   - Weird pages needing manual review

17. Review failures manually or with AI
   - Send only the failed page snippet / parsed section to AI
   - Have it suggest selector fixes or normalization fixes

18. Update extractor/config
   - Adjust selectors
   - Add edge-case handling
   - Re-run from cached HTML, not the network

19. Re-run validation
   - Raw validation
   - Final validation
   - Relationship validation

20. Promote final data into your app/wiki
   - Use final normalized JSON as source of truth
