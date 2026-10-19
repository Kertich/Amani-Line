from dataclasses import dataclass
from typing import Any


COPY = {
    "en": {
        "language": "Choose language:\n1 English\n2 Kiswahili",
        "main": "Amani Line\n1 Local alerts\n2 Report an issue\n3 Check report status\n4 Emergency contacts\n5 Verify info",
        "invalid_main": "Choose 1-5.\n" + "Amani Line\n1 Alerts 2 Report\n3 Status 4 Emergency\n5 Verify",
        "report_type": "Report type:\n1 Rumour to check\n2 Local issue\n3 Safety concern",
        "description": "Briefly describe the issue (max 140 characters):",
        "reference": "Enter your reference (AMN-XXXXXX):",
        "emergency": "Emergency: Police 999/112\nAmbulance 999/112\nEND",
        "invalid": "Invalid choice. Try again.",
        "report_saved": "Report received. Ref: {reference}",
        "bad_description": "Description too long. Dial again to retry.",
        "bad_reference": "Reference not found. Check it and try again.",
        "status": "{reference}: {status}",
        "no_alerts": "No community updates yet.",
        "alert": "{status} | {source} | {date} | {publisher}\n{title}{correction}",
        "unavailable": "Service unavailable. Try again later.",
    },
    "sw": {
        "language": "Chagua lugha:\n1 English\n2 Kiswahili",
        "main": "Amani Line\n1 Tahadhari\n2 Ripoti tatizo\n3 Hali ya ripoti\n4 Dharura\n5 Hakiki habari",
        "invalid_main": "Chagua 1-5.\nAmani Line\n1 Tahadhari 2 Ripoti\n3 Hali 4 Dharura\n5 Hakiki",
        "report_type": "Aina ya ripoti:\n1 Uvumi wa hakiki\n2 Tatizo la eneo\n3 Usalama",
        "description": "Eleza tatizo kwa ufupi (herufi 140):",
        "reference": "Weka nambari (AMN-XXXXXX):",
        "emergency": "Dharura: Polisi 999/112\nAmbulensi 999/112\nEND",
        "invalid": "Chaguo si sahihi. Jaribu tena.",
        "report_saved": "Ripoti imepokelewa. Na.: {reference}",
        "bad_description": "Maelezo ni marefu. Piga tena kujaribu.",
        "bad_reference": "Nambari haijapatikana. Angalia ujaribu tena.",
        "status": "{reference}: {status}",
        "no_alerts": "Hakuna taarifa kwa sasa.",
        "alert": "{status} | {source} | {date} | {publisher}\n{title}{correction}",
        "unavailable": "Huduma haipatikani. Jaribu tena baadaye.",
    },
}


@dataclass(frozen=True)
class UssdResult:
    response: str
    action: str | None = None
    data: dict[str, str] | None = None
    language: str | None = None


def _reply(text: str, language: str, *, end: bool = False, action: str | None = None,
           data: dict[str, str] | None = None) -> UssdResult:
    prefix = "END " if end else "CON "
    return UssdResult(prefix + text[:155], action=action, data=data, language=language)


def handle_ussd(
    history: str,
    *,
    updates: list[dict[str, Any]] | None = None,
    report_status: dict[str, Any] | None = None,
) -> UssdResult:
    steps = history.split("*") if history else []
    if not steps:
        return _reply(COPY["en"]["language"], "en")
    if steps[0] not in {"1", "2"}:
        return _reply(COPY["en"]["language"], "en")

    language = "en" if steps[0] == "1" else "sw"
    copy = COPY[language]
    if len(steps) == 1:
        return _reply(copy["main"], language)

    selection = steps[1]
    if selection == "1":
        if updates is None:
            return UssdResult("", action="updates", language=language)
        if not updates:
            return _reply(copy["no_alerts"], language, end=True)
        item = updates[0]
        status_labels = {
            "confirmed": "Confirmed" if language == "en" else "Imethibitishwa",
            "false": "False" if language == "en" else "Si kweli",
            "pending": "Pending" if language == "en" else "Inasubiri",
        }
        workflow = str(item.get("workflow_status") or "published")
        if workflow == "retracted":
            status_label = "RETRACTED" if language == "en" else "IMEBATILISHWA"
        elif workflow == "corrected":
            status_label = "CORRECTED" if language == "en" else "IMESAHIHISHWA"
        else:
            status_label = status_labels.get(str(item.get("status")), str(item.get("status")))
        date_value = (
            item.get("activity_at")
            if workflow in {"corrected", "retracted"}
            else item.get("published_at") or item.get("created_at")
        )
        date = str(date_value or "")[:10]
        source = str(item.get("source") or ("Not listed" if language == "en" else "Haijaorodheshwa"))
        publisher = str(item.get("publisher_label") or ("Publisher unavailable" if language == "en" else "Mchapishaji hajatajwa"))
        title = str(item.get("title") or "")
        correction_reason = str(item.get("correction_reason") or "")
        correction = (
            f" | {('Reason' if language == 'en' else 'Sababu')}: {correction_reason}"
            if workflow in {"corrected", "retracted"} and correction_reason
            else ""
        )
        return _reply(
            copy["alert"].format(
                status=status_label,
                source=source[:24],
                date=date,
                publisher=publisher.replace("Verified by ", "")[:38],
                title=title[:34],
                correction=correction[:35],
            ),
            language,
            end=True,
        )

    if selection == "5":
        if len(steps) < 3:
            return _reply(copy["description"], language)
        description = "*".join(steps[2:]).strip()
        if not description or len(description) > 140:
            return _reply(copy["bad_description"], language, end=True)
        return UssdResult(
            "",
            action="create_report",
            data={"report_type": "Rumour to check", "description": description},
            language=language,
        )

    if selection == "2":
        report_type = steps[2] if len(steps) > 2 else None
        if report_type is None:
            return _reply(copy["report_type"], language)
        report_types = {
            "1": "Rumour to check",
            "2": "Local issue",
            "3": "Safety concern",
        }
        if report_type not in report_types:
            return _reply(copy["report_type"], language)
        if len(steps) <= 3:
            return _reply(copy["description"], language)
        description = "*".join(steps[3:]).strip()
        if not description or len(description) > 140:
            return _reply(copy["bad_description"], language, end=True)
        return UssdResult(
            "",
            action="create_report",
            data={"report_type": report_types[report_type], "description": description},
            language=language,
        )

    if selection == "3":
        if len(steps) < 3:
            return _reply(copy["reference"], language)
        reference = steps[2].strip().upper()
        if report_status is None:
            return UssdResult("", action="status", data={"reference": reference}, language=language)
        if not report_status:
            return _reply(copy["bad_reference"], language, end=True)
        labels = {"pending": "Pending", "reviewing": "Being reviewed", "resolved": "Resolved"}
        if language == "sw":
            labels = {"pending": "Inasubiri", "reviewing": "Inakaguliwa", "resolved": "Imetatuliwa"}
        return _reply(
            copy["status"].format(reference=reference, status=labels.get(report_status["status"], report_status["status"])),
            language,
            end=True,
        )

    if selection == "4":
        return _reply(copy["emergency"].replace("\nEND", ""), language, end=True)

    return _reply(copy["invalid_main"], language)


def format_sms_status(reference: str, status: str, language: str) -> str:
    labels = {
        "en": {"pending": "Pending", "reviewing": "Being reviewed", "resolved": "Resolved", "dismissed": "Closed"},
        "sw": {"pending": "Inasubiri", "reviewing": "Inakaguliwa", "resolved": "Imetatuliwa", "dismissed": "Imefungwa"},
    }
    return f"{reference}: {labels[language].get(status, status)}"


def format_sms_alert(item: dict[str, Any], language: str) -> str:
    source = str(item.get("source") or ("Not listed" if language == "en" else "Haijaorodheshwa"))
    workflow = str(item.get("workflow_status") or "published")
    date_value = (
        item.get("activity_at")
        if workflow in {"corrected", "retracted"}
        else item.get("published_at") or item.get("created_at")
    )
    date = str(date_value or "")[:10]
    label = {
        "en": {"confirmed": "Confirmed", "false": "False", "pending": "Pending"},
        "sw": {"confirmed": "Imethibitishwa", "false": "Si kweli", "pending": "Inasubiri"},
    }[language].get(str(item.get("status")), str(item.get("status")))
    if workflow == "retracted":
        label = "RETRACTED" if language == "en" else "IMEBATILISHWA"
    elif workflow == "corrected":
        label = "CORRECTED" if language == "en" else "IMESAHIHISHWA"
    publisher = str(item.get("publisher_label") or ("Publisher unavailable" if language == "en" else "Mchapishaji hajatajwa"))
    publisher = publisher.replace("Verified by ", "")[:34]
    reason = str(item.get("correction_reason") or "")
    prefix = f"{label} | {source[:24]} | {date} | {publisher}: "
    if workflow in {"corrected", "retracted"} and reason:
        prefix += f"Reason: {reason[:24]} | "
    return f"{prefix}{item.get('title', '')}"[:155]
