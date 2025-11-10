import frappe
from datetime import datetime, timedelta, time

def get_settings():
    """Fetch custom app settings."""
    return frappe._dict({
        "enable_punctuality_rule": frappe.db.get_single_value("Attendance Rule Settings", "enable_punctuality_rule") or 0,
        "max_violations": frappe.db.get_single_value("Attendance Rule Settings", "max_violations") or 3,
        "auto_half_day": frappe.db.get_single_value("Attendance Rule Settings", "auto_half_day") or 1,
    })


def _normalize_time(value):
    """Convert timedelta → time if needed."""
    if isinstance(value, timedelta):
        return (datetime.min + value).time()
    return value


def validate_punctuality_rule(doc, method):
    """Apply late/early detection using shift grace and custom rule settings."""
    settings = get_settings()
    if not settings.enable_punctuality_rule:
        return

    if doc.status != "Present" or not doc.shift:
        return

    shift = frappe.get_doc("Shift Type", doc.shift)
    if not shift.start_time or not shift.end_time:
        return

    # Normalize shift times (handle timedelta type)
    shift_start = _normalize_time(shift.start_time)
    shift_end = _normalize_time(shift.end_time)

    # Use grace from Shift Type (in minutes)
    late_grace = timedelta(minutes=shift.late_entry_grace_period or 0)
    early_grace = timedelta(minutes=shift.early_exit_grace_period or 0)

    late = early = False
    remarks = None

    # --- Late Entry ---
    if doc.in_time:
        in_diff = datetime.combine(doc.attendance_date, doc.in_time.time()) - datetime.combine(doc.attendance_date, shift_start)
        if in_diff > late_grace:
            late = True
            remarks = f"Late entry by {int(in_diff.total_seconds() // 60)} mins."

    # --- Early Exit ---
    if doc.out_time:
        out_diff = datetime.combine(doc.attendance_date, shift_end) - datetime.combine(doc.attendance_date, doc.out_time.time())
        if out_diff > early_grace:
            early = True
            remarks = f"Left early by {int(out_diff.total_seconds() // 60)} mins."

    if not (late or early):
        return

    violation_type = "Late Entry" if late else "Early Exit"

    # Create Violation Log
    log = frappe.get_doc({
        "doctype": "Punctuality Violation Log",
        "employee": doc.employee,
        "employee_name": doc.employee_name,
        "attendance_date": doc.attendance_date,
        "shift": doc.shift,
        "in_time": doc.in_time,
        "out_time": doc.out_time,
        "violation_type": violation_type,
        "remarks": remarks,
        "attendance": doc.name,
        "auto_flagged": 1
    })
    log.insert(ignore_permissions=True)

    # --- Monthly violation tracking ---
    start_month = doc.attendance_date.replace(day=1)
    end_month = (start_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    count = frappe.db.count(
        "Punctuality Violation Log",
        filters={
            "employee": doc.employee,
            "attendance_date": ["between", [start_month, end_month]],
        }
    )

    if settings.auto_half_day and count > settings.max_violations:
        doc.db_set("status", "Half Day")
        frappe.msgprint(
            f"⚠️ {doc.employee_name} marked Half Day due to repeated late/early check-ins (Occurrence #{count})."
        )
