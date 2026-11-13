### AITSPL Integration

HR, Biometric, Print Formats

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app aitspl_integration
```

### eSSL report import

After updating the app, run `bench setup requirements` and `bench --site <site> migrate`,
then restart the bench processes. A background worker for the `long` queue must be running.
Open **eSSL Attendance Import** from Desk search, or visit `/app/essl-attendance-import`.
HR User, HR Manager and System Manager roles can access the page; normal Employee,
Employee Checkin and Attendance permissions still apply.

1. Select the company and upload an eSSL **Monthly Status Report (Detailed Work Duration)**
   binary `.xls` file (single month, up to 5 MB / 10,000 attendance days).
2. Click **Preview / validate**. Suggestions compare report codes against Employee IDs,
   Employee Numbers and numeric ID suffixes, together with exact employee names.
   A unique exact name can also suggest a match. Device IDs are never used.
3. Review every suggested employee and select ERPNext employees for unresolved matches.
   Conflicting codes/names and duplicate names need manual mapping. Mapping two report
   employees to the same ERPNext employee is blocked. Validate again after edits.
4. Review dates, status, duration, missing punches, assigned ERPNext shifts and existing records.
   Shift codes in the file are ignored. Submitted active Shift Assignments for the date
   take precedence over the Employee default shift. Unresolvable multiple shifts block
   that day; missing shifts are displayed as warnings.
5. Click **Import**. Attendance is created as drafts unless **Submit created Attendance**
   is checked. Submission invokes the app's existing punctuality/overtime hooks.
   Imports run in the background; the page shows totals and failed days. Reopen it in
   the same browser tab to resume monitoring a running import.

The report's attendance status and net work duration are used; ERPNext validation
(including approved leave) still runs. `P`/`WOP`/`HP` map to Present, `A` to Absent,
and `½P`/`H½P` to Half Day. `WO` and `H` without punches are skipped.
Only days with both valid IN and OUT punches are imported. Missing or invalid punches
skip the employee/day entirely: no Checkins and no Attendance of any status, including
Absent or Half Day. Earlier OutTime values roll over to the following day; equal
timestamps and Absent status conflicting with punches are skipped. Malformed report
rows are reported and skipped while valid days can proceed. Missing punches are never
reconstructed from duration.

Any existing non-cancelled Attendance causes the entire employee/day to be skipped.
Otherwise, existing same-timestamp Checkins are reused, including synced punches with
blank directions. Existing punch times/directions are preserved; reused Checkins require
write permission. Imported/reused Checkins are linked to the new Attendance and marked
to skip auto attendance, preventing the scheduler from processing the same report day.
Each failed day rolls back its records together and appears in the result; successful
days remain imported. Re-imports skip those days. Employee mappings are reviewed per
upload and do not alter Employee master data.

The sample report used for verification contained 20 employees, 476 attendance days,
and 29 days with incomplete punches. Personal source files are not bundled with the app.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/aitspl_integration
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
