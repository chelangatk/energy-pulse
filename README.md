# Energy Pulse

A self-updating tracker for North American power market news: ISOs/RTOs
(ERCOT, MISO, SPP, PJM, CAISO, NYISO, ISO-NE), FERC/NERC/DOE, trade press,
data center & load growth coverage, and DER/grid modernization. Runs
entirely on GitHub — no server, no hosting cost.

**Live site** (once deployed): `https://<your-username>.github.io/energy-pulse/`

## How it works

1. **`scripts/fetch_feeds.py`** reads `config/feeds.yaml`, pulls each source
   (RSS/Atom, or a lightweight HTML link-scrape for sites without clean RSS),
   dedupes against history, drops anything older than `retention_days`, and
   writes `docs/data/articles.json`.
2. **`scripts/send_digest.py`** builds a per-category digest from that data,
   saves it to `docs/digests/<date>.md`, and — if configured — emails it
   and/or posts it to Slack.
3. **`.github/workflows/update.yml`** runs both scripts on a schedule
   (default: twice daily), commits the updated data, and (re)deploys
   `docs/` to GitHub Pages.
4. **`docs/`** is a static site (plain HTML/CSS/JS, no build step) that reads
   `articles.json` client-side — searchable, filterable by category.

## Setup (10 minutes)

1. **Create the repo.** Push this folder to a new GitHub repo, e.g.
   `energy-pulse`.
   ```bash
   cd energy-pulse
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/energy-pulse.git
   git push -u origin main
   ```

2. **Enable GitHub Pages.** Repo → Settings → Pages → Source → set to
   **GitHub Actions** (not "Deploy from branch" — the workflow handles it).

3. **Run it once manually.** Repo → Actions → "Update Energy Pulse" →
   Run workflow. This populates `docs/data/articles.json` and does the
   first Pages deploy. After that it runs automatically on the schedule
   in `update.yml` (default 7am / 5pm Central).

4. **(Optional) Set up the email or Slack digest.** Repo → Settings →
   Secrets and variables → Actions → New repository secret:
   - For email: `SMTP_HOST`, `SMTP_PORT` (usually `587`), `SMTP_USER`,
     `SMTP_PASS`, `DIGEST_TO`. Works with Gmail (use an
     [app password](https://myaccount.google.com/apppasswords), not your
     normal password), Outlook, SendGrid, etc.
   - For Slack: `SLACK_WEBHOOK_URL` — create an
     [incoming webhook](https://api.slack.com/messaging/webhooks) in
     whatever channel/workspace you want the digest posted to.
   - Leave either unset and that delivery method is silently skipped —
     the digest markdown is still saved to `docs/digests/` either way.

That's it — the dashboard and the digest are both live and self-updating.

## Customizing

- **Add/remove sources:** edit `config/feeds.yaml`. Most orgs publish RSS at
  a predictable path; if a source you want doesn't have one, add it with
  `html: true` and the fetcher will fall back to scraping headline links
  (less reliable — check the output after a run and tune if needed).
- **Change update frequency:** edit the `cron` lines in
  `.github/workflows/update.yml` ([crontab.guru](https://crontab.guru) helps).
- **Change retention / digest size:** `retention_days` and
  `digest_items_per_category` in `config/feeds.yaml`.
- **Restyle the site:** everything's in `docs/style.css` — no build tooling,
  just edit and push.

## Notes for South Central / ERCOT-focused use

The default `feeds.yaml` already leans toward the categories most relevant
to distribution planning and grid modernization work: ISO/RTO operational
news (including ERCOT), regulatory filings (FERC/NERC), data center and
load-growth coverage (the dominant driver of ERCOT's recent record peaks),
and DER/grid-mod trade press. A few sources worth adding if you want to go
deeper on Texas specifically:

- **PUCT (Public Utility Commission of Texas)** filings/news
- **Oncor, CenterPoint, AEP Texas** newsrooms (your likely utility clients)
- **Doug Lewin's Texas Energy and Power Newsletter** (Substack RSS) —
  widely read independent ERCOT analysis
- **ERCOT Board/TAC meeting materials** if you want to track market design
  changes upstream of planning decisions

Add any of these to `config/feeds.yaml` the same way as the existing entries.
