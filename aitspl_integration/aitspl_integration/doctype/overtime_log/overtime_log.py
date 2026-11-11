# Copyright (c) 2025, info@aitspl.com and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate, get_time

from aitspl_integration.attendance.overtime import get_min_ot_hours


class OvertimeLog(Document):
	def validate(self):
		self.calculate_overtime_hours()

	def calculate_overtime_hours(self):
		"""Calculate overtime for manual entries as well as attendance-created logs."""
		field = self.meta.get_field("overtime_hours")
		numeric_hours = field.fieldtype in ("Float", "Currency", "Int")
		self.overtime_hours = 0 if numeric_hours else "0:00:00"
		if not (self.shift and self.attendance_date and self.in_time and self.out_time):
			return

		shift = frappe.get_doc("Shift Type", self.shift)
		if not (shift.start_time is not None and shift.end_time is not None):
			return

		shift_start = datetime.combine(getdate(self.attendance_date), get_time(shift.start_time))
		shift_end = datetime.combine(getdate(self.attendance_date), get_time(shift.end_time))
		if shift_end < shift_start:
			shift_end += timedelta(days=1)

		in_time = get_datetime(self.in_time)
		out_time = get_datetime(self.out_time)
		if out_time < in_time:
			frappe.throw("Out Time must be after In Time.")

		shift_duration = shift_end - shift_start
		if out_time - in_time < shift_duration:
			return

		overtime_start = max(shift_end, in_time + shift_duration)
		overtime = out_time - overtime_start
		if overtime.total_seconds() <= 0:
			return
		if round(overtime.total_seconds() / 3600, 2) < get_min_ot_hours():
			return

		self.overtime_hours = overtime.total_seconds() / 3600 if numeric_hours else str(overtime)
