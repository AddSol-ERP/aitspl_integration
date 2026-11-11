from datetime import timedelta

import frappe


def duration_in_hours(value):
    """Convert the duration stored by Overtime Log to decimal hours."""
    if isinstance(value, timedelta):
        return value.total_seconds() / 3600

    value = str(value or "0").strip()
    if ":" not in value:
        return float(value)

    days = 0
    if "day" in value:
        day_part, value = value.split(",", 1)
        days = int(day_part.split()[0])
    hours, minutes, seconds = map(float, value.strip().split(":"))
    return days * 24 + hours + minutes / 60 + seconds / 3600


def set_overtime_hours(doc, method=None):
    """Use submitted, approved logs when available; otherwise preserve manual hours."""
    if not (doc.employee and doc.start_date and doc.end_date):
        return

    logs = frappe.get_all(
        "Overtime Log",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [doc.start_date, doc.end_date]],
            "status": "Approved",
            "docstatus": 1,
        },
        fields=["overtime_hours"],
    )
    if logs:
        doc.custom_overtime_hours = sum(duration_in_hours(log.overtime_hours) for log in logs)
