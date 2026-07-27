"""Turn a ClinicalTrials.gov study record into concise, patient-friendly bullets.

The goal is to take a 15-30 page trial protocol (as returned by the API) and
distill it into short, plain-language bullet points that a breast or colon
cancer patient can quickly digest. We deliberately stay faithful to the source
text -- we condense, re-label, and reorganize, but we never invent clinical
facts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

STUDY_PAGE_URL = "https://clinicaltrials.gov/study/{nct_id}"

# Conditions this tool is intended for. Matching is done on lowercased text.
_TARGET_TERMS = {
    "breast": ["breast"],
    "colon": ["colon", "colorectal", "rectal", "rectum", "bowel"],
}

# Plain-language labels for the coded status/phase/type fields.
_STATUS_PLAIN = {
    "RECRUITING": "Open and actively enrolling new patients.",
    "NOT_YET_RECRUITING": "Approved but not yet enrolling patients.",
    "ENROLLING_BY_INVITATION": "Enrolling, but only patients the study team invites.",
    "ACTIVE_NOT_RECRUITING": "Running, but no longer taking new patients.",
    "COMPLETED": "Finished -- the study is no longer enrolling.",
    "SUSPENDED": "Temporarily paused.",
    "TERMINATED": "Stopped early and will not resume.",
    "WITHDRAWN": "Cancelled before any patients enrolled.",
    "UNKNOWN": "Status unknown -- the study has not been updated recently.",
}

_PHASE_PLAIN = {
    "EARLY_PHASE1": "Early Phase 1 (very first human testing, safety focus)",
    "PHASE1": "Phase 1 (early safety and dosing)",
    "PHASE2": "Phase 2 (does the treatment work, and is it safe?)",
    "PHASE3": "Phase 3 (compared against the current standard treatment)",
    "PHASE4": "Phase 4 (long-term study of an already-approved treatment)",
    "NA": "Not applicable (this study does not test a drug in the usual phases)",
}

_STUDY_TYPE_PLAIN = {
    "INTERVENTIONAL": "Interventional -- patients receive a treatment being tested.",
    "OBSERVATIONAL": "Observational -- researchers observe patients without assigning a treatment.",
    "EXPANDED_ACCESS": "Expanded access -- a way to get an investigational treatment outside a trial.",
}

_INTERVENTION_TYPE_PLAIN = {
    "DRUG": "Drug",
    "BIOLOGICAL": "Biologic",
    "DEVICE": "Device",
    "PROCEDURE": "Procedure",
    "RADIATION": "Radiation therapy",
    "BEHAVIORAL": "Behavioral",
    "GENETIC": "Genetic",
    "DIETARY_SUPPLEMENT": "Dietary supplement",
    "COMBINATION_PRODUCT": "Combination product",
    "DIAGNOSTIC_TEST": "Diagnostic test",
    "OTHER": "Other",
}

_SEX_PLAIN = {
    "ALL": "Open to all sexes",
    "FEMALE": "Female patients only",
    "MALE": "Male patients only",
}

# How many bullets we keep for inherently long lists, to stay "concise".
_MAX_CRITERIA = 6
_MAX_INTERVENTIONS = 6
_MAX_LOCATIONS = 5


def summarize_study(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured, patient-friendly summary from raw study JSON."""
    protocol = data.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    nct_id = ident.get("nctId", "")

    summary: Dict[str, Any] = {
        "nct_id": nct_id,
        "title": ident.get("briefTitle") or ident.get("officialTitle") or "Untitled study",
        "url": STUDY_PAGE_URL.format(nct_id=nct_id) if nct_id else None,
        "relevance": _assess_relevance(protocol),
        "sections": [],
    }

    for builder in (
        _section_overview,
        _section_type_and_phase,
        _section_status,
        _section_interventions,
        _section_eligibility,
        _section_locations,
        _section_contacts,
    ):
        section = builder(protocol)
        if section and section["bullets"]:
            summary["sections"].append(section)

    return summary


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def _section_overview(protocol: Dict[str, Any]) -> Dict[str, Any]:
    desc = protocol.get("descriptionModule", {})
    conditions = protocol.get("conditionsModule", {}).get("conditions", [])

    bullets: List[str] = []
    if conditions:
        bullets.append("Condition(s) studied: " + ", ".join(conditions))

    brief = _clean_text(desc.get("briefSummary", ""))
    if brief:
        for sentence in _first_sentences(brief, 3):
            bullets.append(sentence)

    return {"heading": "What is this study about?", "bullets": bullets}


def _section_type_and_phase(protocol: Dict[str, Any]) -> Dict[str, Any]:
    design = protocol.get("designModule", {})
    bullets: List[str] = []

    study_type = design.get("studyType")
    if study_type:
        bullets.append(_STUDY_TYPE_PLAIN.get(study_type, study_type.title()))

    phases = [p for p in design.get("phases", []) if p]
    if phases:
        readable = "; ".join(_PHASE_PLAIN.get(p, p.replace("_", " ").title()) for p in phases)
        bullets.append("Phase: " + readable)

    enrollment = design.get("enrollmentInfo", {}).get("count")
    if enrollment:
        bullets.append(f"About {enrollment} patients are expected to take part.")

    return {"heading": "Study type and phase", "bullets": bullets}


def _section_status(protocol: Dict[str, Any]) -> Dict[str, Any]:
    status_mod = protocol.get("statusModule", {})
    bullets: List[str] = []

    status = status_mod.get("overallStatus")
    if status:
        bullets.append(_STATUS_PLAIN.get(status, status.replace("_", " ").title()))

    start = status_mod.get("startDateStruct", {}).get("date")
    if start:
        bullets.append(f"Started: {_pretty_date(start)}")

    completion = status_mod.get("primaryCompletionDateStruct", {}).get("date") or \
        status_mod.get("completionDateStruct", {}).get("date")
    if completion:
        bullets.append(f"Expected to finish (main results): {_pretty_date(completion)}")

    return {"heading": "Is it enrolling now?", "bullets": bullets}


def _section_interventions(protocol: Dict[str, Any]) -> Dict[str, Any]:
    interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
    bullets: List[str] = []

    for item in interventions[:_MAX_INTERVENTIONS]:
        name = item.get("name")
        if not name:
            continue
        type_label = _INTERVENTION_TYPE_PLAIN.get(item.get("type", ""), item.get("type", "").title())
        bullets.append(f"{type_label}: {name}" if type_label else name)

    remaining = len(interventions) - _MAX_INTERVENTIONS
    if remaining > 0:
        bullets.append(f"...and {remaining} more.")

    return {"heading": "What is being tested?", "bullets": bullets}


def _section_eligibility(protocol: Dict[str, Any]) -> Dict[str, Any]:
    elig = protocol.get("eligibilityModule", {})
    bullets: List[str] = []

    sex = elig.get("sex")
    if sex:
        bullets.append(_SEX_PLAIN.get(sex, sex.title()))

    age_range = _format_age_range(elig.get("minimumAge"), elig.get("maximumAge"))
    if age_range:
        bullets.append(age_range)

    if elig.get("healthyVolunteers") is True:
        bullets.append("Healthy volunteers may be accepted.")

    inclusion, exclusion = _parse_criteria(elig.get("eligibilityCriteria", ""))
    if inclusion:
        bullets.append("You may be able to join if:")
        bullets.extend(f"   - {c}" for c in inclusion[:_MAX_CRITERIA])
        if len(inclusion) > _MAX_CRITERIA:
            bullets.append(f"   - ...and {len(inclusion) - _MAX_CRITERIA} more requirement(s).")
    if exclusion:
        bullets.append("You may NOT be able to join if:")
        bullets.extend(f"   - {c}" for c in exclusion[:_MAX_CRITERIA])
        if len(exclusion) > _MAX_CRITERIA:
            bullets.append(f"   - ...and {len(exclusion) - _MAX_CRITERIA} more reason(s).")

    return {"heading": "Who can join?", "bullets": bullets}


def _section_locations(protocol: Dict[str, Any]) -> Dict[str, Any]:
    locations = protocol.get("contactsLocationsModule", {}).get("locations", [])
    bullets: List[str] = []

    if not locations:
        return {"heading": "Where is it happening?", "bullets": bullets}

    bullets.append(f"Taking place at {len(locations)} location(s), including:")
    for loc in locations[:_MAX_LOCATIONS]:
        parts = [loc.get("facility"), loc.get("city"), loc.get("state"), loc.get("country")]
        label = ", ".join(p for p in parts if p)
        if label:
            bullets.append(f"   - {label}")
    remaining = len(locations) - _MAX_LOCATIONS
    if remaining > 0:
        bullets.append(f"   - ...and {remaining} more site(s).")

    return {"heading": "Where is it happening?", "bullets": bullets}


def _section_contacts(protocol: Dict[str, Any]) -> Dict[str, Any]:
    contacts = protocol.get("contactsLocationsModule", {}).get("centralContacts", [])
    bullets: List[str] = []

    for contact in contacts:
        name = contact.get("name")
        if not name:
            continue
        details = []
        if contact.get("phone"):
            details.append(f"phone {contact['phone']}")
        if contact.get("email"):
            details.append(f"email {contact['email']}")
        line = name
        if details:
            line += " (" + ", ".join(details) + ")"
        bullets.append(line)

    return {"heading": "Who to contact", "bullets": bullets}


# --------------------------------------------------------------------------- #
# Relevance to breast / colon cancer
# --------------------------------------------------------------------------- #

def _assess_relevance(protocol: Dict[str, Any]) -> Dict[str, Any]:
    conditions = protocol.get("conditionsModule", {}).get("conditions", [])
    keywords = protocol.get("conditionsModule", {}).get("keywords", [])
    haystack = " ".join(conditions + keywords).lower()

    matched: List[str] = []
    for label, terms in _TARGET_TERMS.items():
        if any(term in haystack for term in terms):
            matched.append(label)

    if matched:
        note = "This study is relevant to " + " and ".join(f"{m} cancer" for m in matched) + "."
    else:
        note = (
            "Heads up: this study does not clearly mention breast or colon cancer. "
            "Double-check that it applies to you."
        )
    return {"is_breast_or_colon": bool(matched), "matched": matched, "note": note}


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

def _clean_text(text: str) -> str:
    """Collapse whitespace so multi-line protocol prose reads as one paragraph."""
    return re.sub(r"\s+", " ", text or "").strip()


def _first_sentences(text: str, count: int) -> List[str]:
    """Return up to ``count`` sentences from ``text``."""
    if not text:
        return []
    # Split on sentence-ending punctuation followed by a space.
    pieces = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in pieces if p.strip()][:count]


def _parse_criteria(text: str) -> tuple[List[str], List[str]]:
    """Split raw eligibility text into inclusion and exclusion bullet lists."""
    if not text:
        return [], []

    inclusion: List[str] = []
    exclusion: List[str] = []
    bucket: Optional[List[str]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lowered = line.lower()
        if lowered.startswith("inclusion"):
            bucket = inclusion
            continue
        if lowered.startswith("exclusion"):
            bucket = exclusion
            continue

        # Strip common list markers ("* ", "- ", "1. ", "1) ") from the front.
        cleaned = re.sub(r"^[\-\*•]\s*", "", line)
        cleaned = re.sub(r"^\d+[.)]\s*", "", cleaned).strip()
        if not cleaned:
            continue

        if bucket is None:
            # Criteria listed before any header -- treat as inclusion.
            bucket = inclusion
        bucket.append(_truncate(cleaned, 220))

    return inclusion, exclusion


def _truncate(text: str, limit: int) -> str:
    text = _clean_text(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"  # ellipsis


def _format_age_range(minimum: Optional[str], maximum: Optional[str]) -> Optional[str]:
    has_min = minimum and minimum.upper() != "N/A"
    has_max = maximum and maximum.upper() != "N/A"
    if has_min and has_max:
        return f"Ages {minimum} to {maximum}"
    if has_min:
        return f"Ages {minimum} and older"
    if has_max:
        return f"Up to {maximum}"
    return None


def _pretty_date(date_str: str) -> str:
    """Turn '2023-06' or '2023-06-15' into 'June 2023' / 'June 15, 2023'."""
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    parts = date_str.split("-")
    try:
        if len(parts) == 3:
            year, month, day = parts
            return f"{months[int(month) - 1]} {int(day)}, {year}"
        if len(parts) == 2:
            year, month = parts
            return f"{months[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        pass
    return date_str
