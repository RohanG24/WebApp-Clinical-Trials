"""Estimate the patient *burden* of a trial: time toxicity and side effects.

"Time toxicity" is the time a treatment takes out of a patient's life -- clinic
visits, infusions, hospital stays, and how long the whole commitment lasts. It
is one of the things patients care about most and one of the things a standard
trial listing buries. ClinicalTrials.gov has no single tidy field for it, so we
pull the signal from where it actually lives:

* how long the study runs (start -> completion dates),
* how often treatment is given (dosing cadence in the intervention/arm text),
* visit / hospital-stay language in the detailed protocol description.

For side effects we prefer *observed* data: when a study has posted results, the
adverse-events section lists real event rates. When it has not (common while a
trial is still enrolling), we say so plainly rather than guessing.

Everything here stays faithful to the source -- we extract and rephrase what the
record says, flag estimates as estimates, and never invent clinical facts.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple

# Fields that tend to describe the treatment schedule in prose.
_CONFIRM_NOTE = (
    "These time details come from the study's protocol text and may be "
    "incomplete -- confirm the exact visit schedule with the study team."
)

_MAX_SIDE_EFFECTS = 6
_MAX_SERIOUS = 4
_MAX_VISIT_SNIPPETS = 3

# Lightweight bold markers. The client turns [[b]]...[[/b]] into <strong>,
# building DOM nodes (never innerHTML) so external trial text stays inert.
def _b(value: Any) -> str:
    return f"[[b]]{value}[[/b]]"


# --------------------------------------------------------------------------- #
# Time toxicity
# --------------------------------------------------------------------------- #

def assess_time_toxicity(protocol: Dict[str, Any]) -> Dict[str, Any]:
    """Build the 'time commitment' section from a protocolSection dict."""
    bullets: List[str] = []

    duration = _study_duration(protocol)
    if duration:
        bullets.append(duration)

    text_blob = _schedule_text(protocol)

    cadence = _extract_cadence(text_blob)
    if cadence:
        bullets.append("How often treatment is given: " + _b(cadence) + ".")

    cycle = _extract_cycle(text_blob)
    if cycle:
        cycle = re.sub(r"(\d+-(?:day|week) cycles?)", lambda m: _b(m.group(1)), cycle)
        bullets.append("Treatment is given " + cycle + ".")

    visits = _extract_visit_mentions(text_blob)
    for snippet in visits:
        # Bold any counts inside the visit sentence (e.g. "day 1", "2 nights").
        snippet = re.sub(r"\b(\d+)\b", lambda m: _b(m.group(1)), snippet)
        bullets.append(snippet)

    if not cadence and not cycle and not visits:
        bullets.append(
            "This record doesn't spell out how often you'd have visits or how "
            "long you'd stay in hospital. This is an important question about "
            "your time -- ask the study team directly."
        )

    if bullets:
        bullets.append(_CONFIRM_NOTE)

    return {
        "heading": "Your time commitment (time toxicity)",
        "icon": "clock",
        "featured": True,
        "bullets": bullets,
    }


def _study_duration(protocol: Dict[str, Any]) -> Optional[str]:
    status = protocol.get("statusModule", {})
    start = status.get("startDateStruct", {}).get("date")
    end = (
        status.get("primaryCompletionDateStruct", {}).get("date")
        or status.get("completionDateStruct", {}).get("date")
    )
    if not start or not end:
        return None

    span = _month_span(start, end)
    if span is None:
        return None

    human = _humanize_months(span)
    return (
        f"This study runs for roughly {_b(human)} overall "
        f"(from {_year_month(start)} to {_year_month(end)}). Your own time in "
        "the study may be shorter -- ask how long you would take part."
    )


def _schedule_text(protocol: Dict[str, Any]) -> str:
    parts: List[str] = []
    desc = protocol.get("descriptionModule", {})
    parts.append(desc.get("detailedDescription", "") or "")
    parts.append(desc.get("briefSummary", "") or "")

    arms_mod = protocol.get("armsInterventionsModule", {})
    for arm in arms_mod.get("armGroups", []) or []:
        parts.append(arm.get("description", "") or "")
    for item in arms_mod.get("interventions", []) or []:
        parts.append(item.get("description", "") or "")

    return re.sub(r"\s+", " ", " ".join(parts)).strip()


# Dosing cadence phrases -> patient-friendly wording. Order matters: more
# specific patterns are tried first.
def _extract_cadence(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower()

    m = re.search(r"every\s+(\d+)\s+(day|days|week|weeks|month|months)", low)
    if m:
        n, unit = m.group(1), m.group(2).rstrip("s")
        return f"about every {n} {unit}{'s' if int(n) != 1 else ''}"

    m = re.search(r"\bq(\d+)\s*w\b", low)  # Q3W style
    if m:
        return f"about every {m.group(1)} weeks"
    m = re.search(r"\bq(\d+)\s*d\b", low)
    if m:
        return f"about every {m.group(1)} days"

    fixed = [
        (r"\b(twice|two times)\s+(a\s+day|daily)\b", "twice a day"),
        (r"\b(three times)\s+(a\s+day|daily)\b", "three times a day"),
        (r"\bbid\b", "twice a day"),
        (r"\btid\b", "three times a day"),
        (r"\bonce\s+(a\s+day|daily)\b", "once a day"),
        (r"\bqd\b", "once a day"),
        (r"\b(once\s+)?weekly\b|\bonce\s+a\s+week\b|\bqw\b", "about once a week"),
        (r"\b(once\s+)?monthly\b|\bonce\s+a\s+month\b", "about once a month"),
        (r"\bdaily\b", "every day"),
    ]
    for pattern, phrase in fixed:
        if re.search(pattern, low):
            return phrase
    return None


def _extract_cycle(text: str) -> Optional[str]:
    if not text:
        return None
    low = text.lower()
    m = re.search(r"(\d+)[-\s]day\s+cycle", low)
    if m:
        return f"in repeating {m.group(1)}-day cycles"
    m = re.search(r"(\d+)[-\s]week\s+cycle", low)
    if m:
        return f"in repeating {m.group(1)}-week cycles"
    if re.search(r"\bcycle(s)?\b", low):
        return "in repeating treatment cycles"
    return None


_VISIT_KEYWORDS = re.compile(
    r"\b(hospitali[sz]|inpatient|overnight|admitted|admission|infusion|"
    r"clinic visit|study visit|outpatient|hospital stay)\w*",
    re.IGNORECASE,
)


# Sentences that are really just the dosing schedule are already summarized by
# the cadence/cycle bullets, so we skip them as visit snippets to avoid repeats.
_DOSING_ONLY = re.compile(
    r"every\s+\d+\s+(day|week|month)|\d+[-\s](day|week)\s+cycle",
    re.IGNORECASE,
)


def _extract_visit_mentions(text: str) -> List[str]:
    """Pull short sentences that mention visits, infusions, or hospital stays."""
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    found: List[str] = []
    seen = set()
    for sentence in sentences:
        if _DOSING_ONLY.search(sentence):
            continue
        if _VISIT_KEYWORDS.search(sentence):
            clean = sentence.strip()
            if len(clean) > 240:
                clean = clean[:239].rstrip() + "…"
            key = clean.lower()
            if key not in seen:
                seen.add(key)
                found.append(clean)
        if len(found) >= _MAX_VISIT_SNIPPETS:
            break
    return found


# --------------------------------------------------------------------------- #
# Side effects
# --------------------------------------------------------------------------- #

def assess_side_effects(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build the 'possible side effects' section from the full study record."""
    results = data.get("resultsSection", {}) or {}
    ae = results.get("adverseEventsModule", {}) or {}

    bullets: List[str] = []

    common = _top_events(ae.get("otherEvents", []), _MAX_SIDE_EFFECTS)
    serious = _top_events(ae.get("seriousEvents", []), _MAX_SERIOUS)

    if common or serious:
        if common:
            bullets.append("Most commonly reported side effects:")
            bullets.extend(f"   - {label}" for label in common)
        if serious:
            bullets.append("Serious side effects that were reported:")
            bullets.extend(f"   - {label}" for label in serious)
        bullets.append(
            "These rates come from patients already studied. Your experience "
            "may differ -- ask the study team what to watch for."
        )
    else:
        interventions = (
            data.get("protocolSection", {})
            .get("armsInterventionsModule", {})
            .get("interventions", [])
        )
        names = ", ".join(i.get("name", "") for i in interventions if i.get("name"))
        note = (
            "Formal side-effect data has not been posted for this study yet "
            "(this is common while a trial is still enrolling)."
        )
        if names:
            note += f" Ask the study team what side effects to expect from {names}."
        else:
            note += " Ask the study team what side effects to expect."
        bullets.append(note)

    return {
        "heading": "Possible side effects",
        "icon": "activity",
        "featured": True,
        "bullets": bullets,
    }


def _top_events(events: List[Dict[str, Any]], limit: int) -> List[str]:
    """Aggregate adverse-event rates across arms and return the most frequent."""
    scored: List[Tuple[float, str]] = []
    for event in events or []:
        term = event.get("term")
        if not term:
            continue
        affected = 0
        at_risk = 0
        for stat in event.get("stats", []) or []:
            affected += _as_int(stat.get("numAffected"))
            at_risk += _as_int(stat.get("numAtRisk"))
        if at_risk <= 0:
            continue
        rate = affected / at_risk
        scored.append((rate, term))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    labels = []
    for rate, term in scored[:limit]:
        percent = int(math.floor(rate * 100 + 0.5))  # round half up
        labels.append(f"{term} — about {_b(f'{percent}%')} of participants")
    return labels


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_ym(date_str: str) -> Optional[Tuple[int, int]]:
    parts = (date_str or "").split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        return year, month
    except (ValueError, IndexError):
        return None


def _month_span(start: str, end: str) -> Optional[int]:
    a = _parse_ym(start)
    b = _parse_ym(end)
    if not a or not b:
        return None
    months = (b[0] - a[0]) * 12 + (b[1] - a[1])
    return months if months >= 0 else None


def _humanize_months(months: int) -> str:
    if months < 1:
        return "under a month"
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''}"
    years = months // 12
    rem = months % 12
    out = f"{years} year{'s' if years != 1 else ''}"
    if rem:
        out += f" {rem} month{'s' if rem != 1 else ''}"
    return out


_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _year_month(date_str: str) -> str:
    ym = _parse_ym(date_str)
    if not ym:
        return date_str
    year, month = ym
    if 1 <= month <= 12:
        return f"{_MONTHS[month - 1]} {year}"
    return str(year)
