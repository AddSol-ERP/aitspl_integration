import frappe
from datetime import datetime, timedelta, time

def to_time(value):
    """Convert timedelta or datetime.time to datetime.time"""
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time(hours % 24, minutes, seconds)
    return None

def get_min_ot_hours():
    """Fetch configurable minimum OT hours from Attendance Rule Settings."""
    try:
        settings = frappe.get_single("Attendance Rule Settings")
        return float(settings.min_ot_hours or 0.5)
    except Exception:
        # fallback if setting missing or not set
        return 0.5

def create_overtime_log(doc, method=None):
    """Auto-calculate valid overtime considering late entry, full shift duration, and configurable threshold."""
    try:
        emp = frappe.get_doc("Employee", doc.employee)

        # OT not allowed → skip
        if not getattr(emp, "ot_allowed", 0):
            frappe.logger().info(f"OT not allowed for {emp.name}, skipping overtime calculation.")
            return

        if not (doc.shift and doc.in_time and doc.out_time):
            return

        shift = frappe.get_doc("Shift Type", doc.shift)
        if not (shift.start_time and shift.end_time):
            return

        # Convert times safely
        shift_start = to_time(shift.start_time)
        shift_end = to_time(shift.end_time)
        if not (shift_start and shift_end):
            frappe.throw("Invalid shift start/end time format.")

        # Combine with attendance date
        start_dt = datetime.combine(doc.attendance_date, shift_start)
        end_dt = datetime.combine(doc.attendance_date, shift_end)
        in_dt = datetime.combine(doc.attendance_date, doc.in_time.time())
        out_dt = datetime.combine(doc.attendance_date, doc.out_time.time())

        # Handle night shifts or next-day logout
        if out_dt < in_dt:
            out_dt += timedelta(days=1)
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        # Calculate durations
        shift_duration = end_dt - start_dt
        total_worked = out_dt - in_dt

        # No OT if full shift not completed
        if total_worked < shift_duration:
            frappe.logger().info(f"No OT: {emp.name} worked {total_worked}, less than {shift_duration}.")
            return

        # Determine actual OT start
        normal_completion = in_dt + shift_duration
        ot_start_time = max(end_dt, normal_completion)

        if out_dt <= ot_start_time:
            frappe.logger().info(f"No OT: {emp.name} left before OT start {ot_start_time.time()}.")
            return

        # Compute OT hours
        overtime_seconds = (out_dt - ot_start_time).total_seconds()
        overtime_hours = round(overtime_seconds / 3600, 2)

        # Fetch threshold from settings
        min_ot_hours = get_min_ot_hours()
        if overtime_hours < min_ot_hours:
            frappe.logger().info(f"OT below threshold ({overtime_hours} < {min_ot_hours}), skipping.")
            return

        # Create Overtime Log
        log = frappe.get_doc({
            "doctype": "Overtime Log",
            "employee": doc.employee,
            "employee_name": doc.employee_name,
            "attendance_date": doc.attendance_date,
            "attendance": doc.name,
            "shift": doc.shift,
            "in_time": doc.in_time,
            "out_time": doc.out_time,
            "overtime_hours": str(timedelta(seconds=overtime_seconds)),
            "status": "Draft",
            "remarks": f"Worked {total_worked} hrs (OT {str(timedelta(seconds=overtime_seconds))} hrs).",
        })
        log.insert(ignore_permissions=True)

        frappe.msgprint(f"🕒 {overtime_hours} hrs overtime recorded for {doc.employee_name} (awaiting approval).")

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Overtime Log Error")
