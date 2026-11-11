# Copyright (c) 2025, info@aitspl.com and Contributors
# See license.txt

from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from aitspl_integration.aitspl_integration.doctype.overtime_log.overtime_log import OvertimeLog


CONTROLLER = "aitspl_integration.aitspl_integration.doctype.overtime_log.overtime_log"


class TestOvertimeLog(FrappeTestCase):
	def calculate(self, fieldtype="Float", in_time="2026-11-11 09:00:00",
		out_time="2026-11-11 19:30:00", start=None, end=None):
		doc = SimpleNamespace(
			meta=SimpleNamespace(get_field=Mock(return_value=SimpleNamespace(fieldtype=fieldtype))),
			shift="Test Shift", attendance_date="2026-11-11",
			in_time=in_time, out_time=out_time,
		)
		shift = SimpleNamespace(
			start_time=start if start is not None else timedelta(hours=9),
			end_time=end if end is not None else timedelta(hours=17),
		)
		with patch(f"{CONTROLLER}.frappe.get_doc", return_value=shift), patch(
			f"{CONTROLLER}.get_min_ot_hours", return_value=0.5
		):
			OvertimeLog.calculate_overtime_hours(doc)
		return doc.overtime_hours

	def test_numeric_hours(self):
		self.assertEqual(self.calculate(), 2.5)

	def test_general_shift_early_arrival(self):
		self.assertAlmostEqual(self.calculate(
			in_time="2026-11-11 05:56:53", out_time="2026-11-11 23:56:53",
			start=time(9), end=time(19),
		), 4 + 56 / 60 + 53 / 3600)

	def test_duration_hours(self):
		self.assertEqual(self.calculate(fieldtype="Data"), "2:30:00")

	def test_late_entry(self):
		self.assertEqual(self.calculate(in_time="2026-11-11 10:00:00"), 1.5)

	def test_below_threshold(self):
		self.assertEqual(self.calculate(out_time="2026-11-11 17:15:00"), 0)

	def test_incomplete_shift(self):
		self.assertEqual(self.calculate(out_time="2026-11-11 16:00:00"), 0)

	def test_overnight_shift(self):
		self.assertEqual(self.calculate(
			in_time="2026-11-11 22:00:00", out_time="2026-11-12 08:00:00",
			start=time(22), end=time(6),
		), 2)
