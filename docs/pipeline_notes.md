# Page Scraper Pipeline Notes

1. Collect page URLs
   - Use `inputs/page_urls.txt` for generalized input.
   - `inputs/monster_urls.txt` is only compatibility/sample data.

2. Save explicit pages
   - Use the browser UI or scraper scripts to download pages.
   - Direct saves create a job folder under `data/jobs/<site>_<job-id>/`.
   - Pages are written under that job's `pages/` folder.
   - Each page folder contains `source.html`, `content.html`, `content.md`, and `metadata.json`.

3. Refresh derived content
   - Refresh reads existing `source.html`.
   - It rebuilds `content.html`, `content.md`, and `metadata.json`.
   - It does not download from the web.
   - The default refresh command walks `data/jobs/*/pages/`.

4. Discover related pages
   - Use the backend job flow to start from one URL.
   - Discovery applies max-depth, same-domain, and same-start-path boundaries.
   - Discovery records pages, assets, structured events, and structured failures in memory for the active process.

5. Download selected job output
   - Selected pages and assets are written under `data/jobs/<site>_<job-id>/`.
   - Pages keep the same archive model inside the job `pages/` folder.
   - Assets are saved under `assets/images/`, `assets/documents/`, or `assets/other/`.

6. Review the manifest
   - Each job writes `manifest.json`.
   - The manifest records settings, counts, downloaded paths, and failures.
   - SQLite persistence is intentionally not part of the current backend phase.

## Local API Layer

The local API is a thin JSON layer over the current scraper backend. It does not introduce a database or a separate app framework. Frontends should treat `manifest.json` and files under `data/jobs/` as completed output, while using `/api/jobs/{job_id}` and related routes for live in-memory state.
