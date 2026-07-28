"""Search ClinicalTrials.gov for trials by disease, location, and time burden.

The disease and location filters are handled by the official ClinicalTrials.gov
search API (``/api/v2/studies``). Time commitment is not a field the registry
publishes, so we estimate it for each result (see
``burden.estimate_time_commitment``) and filter/sort on that estimate.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from .burden import LEVEL_RANK, estimate_time_commitment
from .fetcher import TrialFetchError

SEARCH_URL = "https://clinicaltrials.gov/api/v2/studies"
STUDY_PAGE_URL = "https://clinicaltrials.gov/study/{nct_id}"

DEFAULT_TIMEOUT = 30
MAX_RESULTS = 25


def search_studies(
    condition: str,
    location: Optional[str] = None,
    max_level: Optional[str] = None,
    recruiting_only: bool = True,
    page_size: int = 50,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Search for trials and return lightweight, patient-friendly result cards."""
    if not condition or not condition.strip():
        raise TrialFetchError("Enter a disease or condition to search for.")

    params: Dict[str, Any] = {
        "query.cond": condition.strip(),
        "pageSize": page_size,
        "countTotal": "true",
    }
    if location and location.strip():
        params["query.locn"] = location.strip()
    if recruiting_only:
        params["filter.overallStatus"] = "RECRUITING"

    try:
        response = requests.get(
            SEARCH_URL, params=params, headers={"Accept": "application/json"}, timeout=timeout
        )
    except requests.exceptions.Timeout as exc:
        raise TrialFetchError("ClinicalTrials.gov took too long to respond. Please try again.") from exc
    except requests.exceptions.RequestException as exc:
        raise TrialFetchError("Could not reach ClinicalTrials.gov. Check the connection and try again.") from exc

    if response.status_code != 200:
        raise TrialFetchError(
            f"ClinicalTrials.gov returned an unexpected error (HTTP {response.status_code})."
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise TrialFetchError("ClinicalTrials.gov returned a response that could not be read.") from exc

    studies = data.get("studies", []) or []
    results = [build_result(study) for study in studies]
    results = [r for r in results if r["nct_id"]]

    if max_level:
        results = filter_by_level(results, max_level)

    # Lightest commitment first; unknown estimates last.
    results.sort(key=lambda r: (r["time"]["rank"], r["title"].lower()))

    return {
        "total_matching": data.get("totalCount"),
        "shown": min(len(results), MAX_RESULTS),
        "results": results[:MAX_RESULTS],
    }


def build_result(study: Dict[str, Any]) -> Dict[str, Any]:
    """Turn one raw study record into a compact result card (no network)."""
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    nct_id = ident.get("nctId", "")
    status = protocol.get("statusModule", {}).get("overallStatus", "")
    conditions = protocol.get("conditionsModule", {}).get("conditions", []) or []
    locations = protocol.get("contactsLocationsModule", {}).get("locations", []) or []

    return {
        "nct_id": nct_id,
        "title": ident.get("briefTitle") or ident.get("officialTitle") or "Untitled study",
        "status": status.replace("_", " ").title() if status else "",
        "conditions": conditions[:4],
        "locations": _summarize_locations(locations),
        "location_count": len(locations),
        "time": estimate_time_commitment(protocol),
        "url": STUDY_PAGE_URL.format(nct_id=nct_id) if nct_id else None,
    }


def filter_by_level(results: List[Dict[str, Any]], max_level: str) -> List[Dict[str, Any]]:
    """Keep results at or below the requested commitment level.

    Studies whose commitment could not be estimated are kept (and flagged in the
    UI) rather than silently hidden, since we cannot rule them in or out.
    """
    ceiling = LEVEL_RANK.get(max_level.title())
    if ceiling is None:
        return results
    kept = []
    for r in results:
        rank = r["time"]["rank"]
        if rank <= ceiling or r["time"]["level"] == "Unknown":
            kept.append(r)
    return kept


def _summarize_locations(locations: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    """Return up to ``limit`` distinct 'City, State/Country' strings."""
    seen = set()
    out: List[str] = []
    for loc in locations:
        parts = [loc.get("city"), loc.get("state"), loc.get("country")]
        label = ", ".join(p for p in parts if p)
        if label and label not in seen:
            seen.add(label)
            out.append(label)
        if len(out) >= limit:
            break
    return out
