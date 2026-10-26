"""Transparent keyword/date extraction for ClarityKit; no web framework required."""
from __future__ import annotations
import re
from datetime import datetime, date
from typing import Any

MAX_TEXT_CHARS = 50_000

CATEGORY_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("Deadline", ("deadline", "due date", "submit by", "submission period", "before the deadline", "by the published deadline", "closes on", "ends on"), "date"),
    ("What to submit", ("must include", "required submission", "what to submit", "submit a", "source code", "demo video", "screenshots", "repository", "setup instructions", "live demo"), "deliverable"),
    ("Eligibility", ("eligible", "eligibility", "ages", "age ", "students only", "all countries", "residents", "participants must", "may participate", "team of up to", "professional organizations excluded"), "eligibility"),
    ("Restrictions & risks", ("not allowed", "do not", "must not", "prohibited", "disqualification", "disqualified", "plagiarism", "private information", "api keys", "passwords", "organizers and judges may not"), "risk"),
    ("Build requirements", ("working prototype", "created during", "during the hackathon", "existing libraries", "frameworks", "apis", "credit", "ai tools", "incomplete features", "simulated functionality"), "build"),
    ("Judging criteria", ("judged on", "judging criteria", "creativity", "impact", "technical execution", "user experience", "design and user experience"), "judging"),
    ("Prizes & recognition", ("prize", "cash", "certificate", "credits", "winner", "first place", "second place", "third place"), "prize"),
]

DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s*,?\s*\d{4}(?:\s*@\s*\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?(?:\s*(?:GMT|UTC)\s*[+-]\d{1,2}(?::\d{2})?)?)?", re.I),
    re.compile(r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2},?\s+\d{4}(?:\s*@\s*\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?(?:\s*(?:GMT|UTC)\s*[+-]\d{1,2}(?::\d{2})?)?)?", re.I),
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{1,2}:\d{2})?\b"),
]

CATEGORY_STYLES = {
    "Deadline": "amber", "What to submit": "blue", "Eligibility": "violet",
    "Restrictions & risks": "red", "Build requirements": "teal",
    "Judging criteria": "green", "Prizes & recognition": "pink",
}


def _sentences(text: str) -> list[str]:
    """Split input into readable evidence units while preserving useful clauses."""
    chunks: list[str] = []
    for line in text.replace("\r", "\n").split("\n"):
        line = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", line)
        chunks.extend(part.strip() for part in parts if part.strip())
    return chunks


def _parse_date(raw: str) -> date | None:
    """Parse common date forms. If the date is ambiguous, return None."""
    clean = raw.split("@")[0].strip().rstrip(".,")
    for fmt in ("%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y", "%Y-%m-%d", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(clean.replace(",", ""), fmt).date()
        except ValueError:
            pass
    return None


def analyze_notice(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS]
    if len(text) < 20:
        raise ValueError("Paste at least 20 characters so ClarityKit has enough context to analyze.")

    units = _sentences(text)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    now = date.today()

    for unit in units:
        low = unit.lower()
        matched: list[str] = []
        for category, keywords, _kind in CATEGORY_RULES:
            if any(keyword in low for keyword in keywords):
                matched.append(category)
        # Date-shaped lines are worth surfacing only if they plausibly relate to an event.
        if any(p.search(unit) for p in DATE_PATTERNS) and any(k in low for k in ("deadline", "submit", "due", "schedule", "oct", "nov", "dec", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "2026", "2027")):
            matched.append("Deadline")
        for category in matched:
            key = (category, re.sub(r"\s+", " ", unit.lower()))
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "category": category,
                "style": CATEGORY_STYLES.get(category, "blue"),
                "evidence": unit[:420],
                "note": _human_note(category),
            })

    # Parse dates from any text; don't label them as deadlines unless nearby wording indicates it.
    dates: list[dict[str, Any]] = []
    raw_seen: set[str] = set()
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0).strip().rstrip(".,")
            if raw.lower() in raw_seen:
                continue
            raw_seen.add(raw.lower())
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].replace("\n", " ")
            context_low = context.lower()
            date_value = _parse_date(raw)
            likely_deadline = any(word in context_low for word in ("deadline", "submit", "due", "submission", "closes", "ends"))
            if date_value:
                days = (date_value - now).days
                if days < 0:
                    timing = "Past date — verify"
                elif days == 0:
                    timing = "Today — verify time zone"
                elif days <= 2:
                    timing = f"{days} day(s) away — soon"
                else:
                    timing = f"{days} days away"
            else:
                timing = "Date found — verify manually"
            dates.append({"raw": raw, "parsed": date_value.isoformat() if date_value else None,
                          "timing": timing, "likely_deadline": likely_deadline,
                          "context": context.strip()[:300]})

    # Surface important absent sections as review prompts, never assert that the document omits them.
    lower = text.lower()
    review_prompts = []
    for label, keys, reason in [
        ("Team size", ("team of up to", "team size", "individual", "solo"), "Confirm whether solo participation or a team-size limit is specified."),
        ("Submission checklist", ("demo video", "source code", "screenshot", "project description"), "Confirm every required submission item, not only the project itself."),
        ("AI disclosure", ("ai tools", "artificial intelligence", "credit ai", "ai assistance"), "Look for an explicit AI-tool disclosure requirement and follow it."),
        ("Project timing", ("created during", "during the hackathon", "submission period"), "Check whether existing projects are allowed or the project must be built during the event."),
    ]:
        if not any(key in lower for key in keys):
            review_prompts.append({"label": label, "reason": reason})

    category_order = ["Deadline", "Eligibility", "What to submit", "Restrictions & risks", "Build requirements", "Judging criteria", "Prizes & recognition"]
    counts = {category: sum(1 for f in findings if f["category"] == category) for category in category_order}
    # Prioritize likely requirements/restrictions; counts are explanation, not a risk score.
    priority_order = {"Restrictions & risks": 0, "Deadline": 1, "Eligibility": 2, "What to submit": 3,
                      "Build requirements": 4, "Judging criteria": 5, "Prizes & recognition": 6}
    findings.sort(key=lambda f: (priority_order.get(f["category"], 9), f["evidence"].lower()))
    return {
        "character_count": len(text),
        "unit_count": len(units),
        "findings": findings,
        "dates": dates,
        "counts": counts,
        "review_prompts": review_prompts,
        "summary": _summary(findings, dates),
        "method": "Keyword-based extraction with quoted evidence. It can miss paraphrases and may surface false positives; verify every item against the original notice.",
    }


def _human_note(category: str) -> str:
    return {
        "Deadline": "Check the exact date, time, time zone, and whether the portal closes earlier than expected.",
        "What to submit": "Treat this as a submission item to verify and tick off before the deadline.",
        "Eligibility": "Compare this statement with your own situation before relying on eligibility.",
        "Restrictions & risks": "Read the original clause carefully; violating a rule could affect eligibility or submission validity.",
        "Build requirements": "Check this while planning the prototype and document any simulated or incomplete behavior.",
        "Judging criteria": "Use this as a guide for what the demo should visibly prove.",
        "Prizes & recognition": "Verify the exact prize, conditions, and cash-versus-credit distinction on the official page.",
    }.get(category, "Verify this item in the original notice.")


def _summary(findings: list[dict[str, Any]], dates: list[dict[str, Any]]) -> str:
    categories = {f["category"] for f in findings}
    parts = []
    if "Deadline" in categories or dates:
        parts.append("dates or deadline language found")
    if "Eligibility" in categories:
        parts.append("eligibility terms surfaced")
    if "What to submit" in categories:
        parts.append("submission deliverables surfaced")
    if "Restrictions & risks" in categories:
        parts.append("restrictions worth reviewing")
    if not parts:
        return "No strong rule keywords were matched. Try pasting the full notice, including its requirements and rules sections."
    return "ClarityKit found " + ", ".join(parts) + ". Review the quoted evidence below; these are prompts, not verified legal or eligibility conclusions."


