# Clinical Trial Summarizer

A small web app that turns a long (15–30 page) clinical trial protocol into a
short, plain-language bullet-point summary. It is built for **breast and colon
cancer patients** who want to quickly understand what a study is about, who can
join, and whether it is enrolling.

You give it a study's **NCT number** (e.g. `NCT05773144`); the app looks up the
study on ClinicalTrials.gov and hands back a digest.

## How it works

```
NCT number  ──►  fetcher  ──►  summarizer  ──►  bullet-point summary
                (API v2)      (plain language)
```

1. **Fetcher** (`clinical_trials/fetcher.py`) — Given an NCT number, it requests
   the study record from the official **ClinicalTrials.gov API v2**:

   ```
   https://clinicaltrials.gov/api/v2/studies/<NCT ID>
   ```

   This is the same data that populates the study page at
   `https://clinicaltrials.gov/study/<NCT ID>`. Because that page is a
   JavaScript single-page app, scraping its rendered HTML is brittle — the API
   returns the same information as clean, structured JSON, so we use it as the
   reliable source.

2. **Summarizer** (`clinical_trials/summarizer.py`) — Condenses the structured
   record into short bullets grouped into patient-friendly sections:
   *What is this study about? · **Your time commitment (time toxicity)** ·
   **Possible side effects** · Study type and phase · Is it enrolling now? ·
   What is being tested? · Who can join? · Where is it happening? · Who to
   contact.* Coded values (e.g. `PHASE2`, `RECRUITING`) are translated into
   plain language, eligibility text is split into simple "you may / may not
   join if…" bullets, and the study is flagged for relevance to breast/colon
   cancer.

3. **Patient burden** (`clinical_trials/burden.py`) — The two highlighted
   sections above are the app's main focus, because they are what patients most
   want to know and what standard listings hide:

   - **Time toxicity** — how much of a patient's life the trial takes up:
     the overall study length (from start/completion dates), how often treatment
     is given and in what cycles (dosing cadence parsed from the protocol text),
     and clinic-visit / infusion / hospital-stay language pulled from the
     detailed description. If the record doesn't spell this out, the app says so
     and tells the patient to ask the study team.
   - **Possible side effects** — when a study has **posted results**, real
     observed adverse-event rates are aggregated across arms and shown most-
     frequent-first (common and serious separately). When results are not yet
     posted (typical for enrolling trials), the app states that plainly instead
     of guessing.

   These are estimates drawn faithfully from the protocol text and are always
   labeled as such, with a prompt to confirm details with the study team.

4. **Web app** (`app.py` + `templates/` + `static/`) — A Flask front end with a
   search box and a JSON endpoint (`/api/summary?nct=...`). The time-toxicity
   and side-effect cards are visually highlighted so they stand out.

The tool stays faithful to the source: it condenses and re-labels information
but never invents clinical facts.

## Running locally

Requires Python 3.9+ and outbound network access to `clinicaltrials.gov`.

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000> and enter an NCT number.

You can also hit the JSON API directly:

```bash
curl "http://127.0.0.1:5000/api/summary?nct=NCT05773144"
```

## Running the tests

The tests cover NCT-number parsing and the summarizer, using a saved sample
study fixture — so they run fully offline (no network needed):

```bash
python -m unittest discover -s tests
```

## Project layout

```
app.py                        Flask app (routes + JSON API)
clinical_trials/
  fetcher.py                  Fetch a study by NCT number (ClinicalTrials.gov API v2)
  summarizer.py               Turn the record into patient-friendly bullets
  burden.py                   Time toxicity + side-effect extraction (main focus)
templates/index.html          Search page
static/style.css, script.js   Front-end styling and logic
tests/                        Unit tests + sample study fixture
```

## Disclaimer

This tool summarizes public information from ClinicalTrials.gov. It is **not
medical advice**. Always confirm details with the study team and your own doctor
before making any decisions.
