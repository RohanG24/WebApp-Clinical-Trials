"""Fetch a study record from ClinicalTrials.gov.

The public ClinicalTrials.gov study pages (``https://clinicaltrials.gov/study/NCTXXXXXXXX``)
are a JavaScript single-page app, so scraping the rendered HTML is brittle. The
same data that populates those pages is served as structured JSON by the
official ClinicalTrials.gov API v2:

    https://clinicaltrials.gov/api/v2/studies/<NCT ID>

We fetch from that endpoint. It is the reliable, officially supported way to
"visit the study page" for a given NCT number and pull back every field the
summarizer needs.
"""

from __future__ import annotations

import re
from typing import Any, Dict

import requests

API_URL = "https://clinicaltrials.gov/api/v2/studies/{nct_id}"
STUDY_PAGE_URL = "https://clinicaltrials.gov/study/{nct_id}"

# NCT numbers are the letters "NCT" followed by exactly 8 digits.
_NCT_RE = re.compile(r"^NCT\d{8}$")

DEFAULT_TIMEOUT = 20  # seconds


class TrialFetchError(Exception):
    """Raised when a study cannot be fetched or the NCT id is invalid."""


def normalize_nct_id(raw: str) -> str:
    """Clean up user input into a canonical NCT id.

    Accepts things like " nct05773144 ", "NCT05773144", or a full study URL and
    returns "NCT05773144". Raises :class:`TrialFetchError` if the value cannot be
    interpreted as a valid NCT number.
    """
    if not raw:
        raise TrialFetchError("Please enter an NCT number.")

    value = raw.strip()

    # Allow pasting a full clinicaltrials.gov URL.
    url_match = re.search(r"(NCT\d{8})", value, flags=re.IGNORECASE)
    if url_match:
        value = url_match.group(1)

    value = value.upper().replace(" ", "")

    # Tolerate a bare number ("05773144") by prefixing NCT.
    if value.isdigit() and len(value) == 8:
        value = "NCT" + value

    if not _NCT_RE.match(value):
        raise TrialFetchError(
            f"'{raw}' is not a valid NCT number. "
            "It should look like NCT05773144 (the letters NCT followed by 8 digits)."
        )
    return value


def fetch_study(nct_id: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Fetch and return the raw study JSON for ``nct_id``.

    ``nct_id`` may be in any form accepted by :func:`normalize_nct_id`.
    """
    canonical = normalize_nct_id(nct_id)
    url = API_URL.format(nct_id=canonical)

    try:
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
    except requests.exceptions.Timeout as exc:
        raise TrialFetchError(
            "ClinicalTrials.gov took too long to respond. Please try again."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise TrialFetchError(
            "Could not reach ClinicalTrials.gov. Check the network connection and try again."
        ) from exc

    if response.status_code == 404:
        raise TrialFetchError(
            f"No study found for {canonical}. Double-check the NCT number."
        )
    if response.status_code != 200:
        raise TrialFetchError(
            f"ClinicalTrials.gov returned an unexpected error (HTTP {response.status_code})."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise TrialFetchError(
            "ClinicalTrials.gov returned a response that could not be read."
        ) from exc

    if "protocolSection" not in data:
        raise TrialFetchError(
            f"The record for {canonical} did not contain the expected study details."
        )

    return data
