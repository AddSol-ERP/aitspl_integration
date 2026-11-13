frappe.pages["essl-attendance-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("eSSL Attendance Import"),
		single_column: true,
	});
	const api = "aitspl_integration.attendance.essl_import.";
	const escape = (value) => frappe.utils.escape_html(String(value == null ? "" : value));
	const root = $('<div class="p-4"></div>').appendTo(page.body);
	root.append(
		$('<p class="text-muted"></p>').text(
			__(
				"Upload an eSSL Detailed Work Duration .xls report. Review employee matches before importing. Shifts come from ERPNext assignments/defaults. Report status and duration are used; missing punches are never inferred."
			)
		)
	);
	const controls = $('<div class="row"></div>').appendTo(root);
	const companyBox = $('<div class="col-md-6"></div>').appendTo(controls);
	const fileBox = $('<div class="col-md-6"></div>').appendTo(controls);
	let fileUrl = null;
	let employeeControls = [];
	let previewData = null;
	let busy = false;
	let importButton, mappingArea, previewArea;
	const company = frappe.ui.form.make_control({
		parent: companyBox,
		render_input: true,
		df: {
			fieldname: "company",
			fieldtype: "Link",
			options: "Company",
			label: __("Company"),
			reqd: 1,
			change: reset,
		},
	});
	const upload = $('<button class="btn btn-default" type="button"></button>')
		.text(__("Upload eSSL report"))
		.appendTo(fileBox);
	const fileLabel = $('<p class="text-muted mt-2"></p>').appendTo(fileBox);
	const submit = frappe.ui.form.make_control({
		parent: root,
		render_input: true,
		df: {
			fieldname: "submit_attendance",
			fieldtype: "Check",
			label: __("Submit created Attendance"),
			description: __(
				"Leave unchecked to create drafts for review. Submission runs existing attendance, punctuality and overtime rules."
			),
			change: invalidate,
		},
	});
	const buttons = $('<div class="my-3"></div>').appendTo(root);
	const previewButton = $('<button class="btn btn-default mr-2" type="button"></button>')
		.text(__("Preview / validate"))
		.appendTo(buttons);
	importButton = $('<button class="btn btn-primary" type="button" disabled></button>')
		.text(__("Import"))
		.appendTo(buttons);
	mappingArea = $('<div class="mt-4"></div>').appendTo(root);
	previewArea = $('<div class="mt-4"></div>').appendTo(root);
	const resultsArea = $('<div class="mt-4"></div>').appendTo(root);
	const storageKey = "essl-import-job:" + frappe.session.user;

	function invalidate() {
		previewData = null;
		if (importButton) importButton.prop("disabled", true);
		if (previewArea) previewArea.empty();
	}
	function reset() {
		invalidate();
		employeeControls = [];
		if (mappingArea) mappingArea.empty();
	}
	function mappings() {
		return Object.fromEntries(
			employeeControls.map(({ code, control }) => [code, control.get_value() || null])
		);
	}
	function args() {
		return {
			file_url: fileUrl,
			company: company.get_value(),
			submit_attendance: submit.get_value() ? 1 : 0,
		};
	}
	function setBusy(value) {
		busy = value;
		upload.prop("disabled", value);
		previewButton.prop("disabled", value);
		importButton.prop("disabled", value || !previewData || previewData.blocked);
		for (const control of [company, submit, ...employeeControls.map((item) => item.control)]) {
			control.df.read_only = value ? 1 : 0;
			control.refresh();
		}
	}
	upload.on("click", () => {
		new frappe.ui.FileUploader({
			allow_multiple: false,
			make_attachments_public: false,
			restrictions: { allowed_file_types: [".xls"], max_file_size: 5 * 1024 * 1024 },
			on_success(file) {
				fileUrl = file.file_url;
				fileLabel.text(file.file_name);
				reset();
				resultsArea.empty();
			},
		});
	});
	previewButton.on("click", async () => {
		if (busy) return;
		if (!fileUrl || !company.get_value()) {
			frappe.msgprint(__("Select a company and upload a report first."));
			return;
		}
		setBusy(true);
		try {
			const request = args();
			delete request.submit_attendance;
			if (employeeControls.length) request.employee_map = JSON.stringify(mappings());
			const response = await frappe.call({
				method: api + "preview",
				args: request,
				freeze: true,
				freeze_message: __("Reading report…"),
			});
			const data = response.message;
			if (!employeeControls.length) renderMappings(data.employees);
			previewData = data;
			renderPreview(data);
		} finally {
			setBusy(false);
		}
	});
	function renderMappings(employees) {
		mappingArea.empty().append($("<h4></h4>").text(__("Employee mapping")));
		mappingArea.append(
			$('<p class="text-muted"></p>').text(
				__(
					"Suggestions use employee code/number and exact names, never biometric device IDs. Correct any suggestion, then validate again."
				)
			)
		);
		const table = $(
			'<table class="table table-bordered"><thead><tr><th>Report code</th><th>Report name</th><th>ERPNext Employee</th><th>Match</th></tr></thead><tbody></tbody></table>'
		).appendTo(mappingArea);
		employeeControls = employees.map((item) => {
			const row = $("<tr></tr>").appendTo(table.find("tbody"));
			row.append($("<td></td>").text(item.code), $("<td></td>").text(item.report_name));
			const input = $('<td style="min-width:260px"></td>').appendTo(row);
			const control = frappe.ui.form.make_control({
				parent: input,
				render_input: true,
				df: {
					fieldname: "employee",
					fieldtype: "Link",
					options: "Employee",
					label: __("Employee"),
					default: item.employee || "",
					change: invalidate,
					get_query: () => ({
						filters: { company: company.get_value(), status: "Active" },
					}),
				},
			});
			control.set_input(item.employee || "");
			row.append($("<td></td>").text(item.reason));
			return { code: item.code, control };
		});
	}
	function renderPreview(data) {
		previewArea.empty();
		const create = data.rows.filter((row) => !row.existing_attendance && !row.skip_reason && !row.error).length;
		const warnings = data.rows.filter((row) => row.warnings.length).length;
		previewArea.append($("<h4></h4>").text(__("Attendance preview")));
		previewArea.append(
			$("<p></p>").text(
				`${data.rows.length} days · ${create} to create · ${
					data.rows.length - create
				} days skipped or unresolved · ${warnings} days with warnings`
			)
		);
		if (data.blocked)
			previewArea.append(
				$('<p class="text-danger"></p>').text(
					__("Resolve the errors and employee mappings, then validate again.")
				)
			);
		for (const error of data.errors)
			previewArea.append(
				$('<p class="text-danger"></p>').text(`${error.source}: ${error.error}`)
			);
		const tableArea = $('<div class="table-responsive"></div>').appendTo(previewArea);
		const pager = $('<div class="my-2"></div>').appendTo(previewArea);
		let offset = 0;
		function draw() {
			const rows = data.rows.slice(offset, offset + 100);
			tableArea.html(
				`<table class="table table-bordered table-sm"><thead><tr><th>Employee</th><th>Date</th><th>Status</th><th>In</th><th>Out</th><th>Hours</th><th>ERPNext shift</th><th>Action / notes</th></tr></thead><tbody>${rows
					.map(
						(row) => `<tr>
				<td>${escape(row.employee || row.employee_code)}</td><td>${escape(row.attendance_date)}</td>
				<td>${escape(row.status)}</td><td>${escape(row.in_time)}</td><td>${escape(row.out_time)}</td>
				<td>${Number(row.working_hours).toFixed(2)}</td><td>${escape(row.shift || "—")}</td>
				<td>${escape(
					[
						row.action,
						row.existing_attendance,
						row.existing_checkins.length
							? `${row.existing_checkins.length} existing punches`
							: "",
						row.error,
						...row.warnings,
					]
						.filter(Boolean)
						.join("; ")
				)}</td>
			</tr>`
					)
					.join("")}</tbody></table>`
			);
			pager.empty();
			$('<button class="btn btn-default btn-sm mr-2">Previous</button>')
				.prop("disabled", offset === 0)
				.on("click", () => {
					offset -= 100;
					draw();
				})
				.appendTo(pager);
			$('<span class="mr-2"></span>')
				.text(
					`${offset + 1}–${Math.min(offset + 100, data.rows.length)} / ${
						data.rows.length
					}`
				)
				.appendTo(pager);
			$('<button class="btn btn-default btn-sm">Next</button>')
				.prop("disabled", offset + 100 >= data.rows.length)
				.on("click", () => {
					offset += 100;
					draw();
				})
				.appendTo(pager);
		}
		draw();
	}
	importButton.on("click", async () => {
		if (busy || !previewData || previewData.blocked) return;
		setBusy(true);
		try {
			const response = await frappe.call({
				method: api + "import_report",
				args: { ...args(), employee_map: JSON.stringify(mappings()) },
				freeze: true,
				freeze_message: __("Importing Attendance and Checkins…"),
			});
			const token = response.message.token;
			sessionStorage.setItem(storageKey, token);
			await monitor(token);
		} finally {
			setBusy(false);
		}
	});
	async function monitor(token) {
		while (true) {
			const response = await frappe.call({ method: api + "import_status", args: { token } });
			const state = response.message;
			resultsArea.empty().append($("<h4></h4>").text(__("Import result")));
			if (state.status === "Completed") {
				const result = state.result;
				resultsArea.append(
					$("<p></p>").text(
						`${result.attendance_created} Attendance created · ${result.checkins_created} Checkins created · ${result.checkins_reused} Checkins reused · ${result.skipped} days skipped · ${result.errors.length} failed or invalid days`
					)
				);
				for (const error of result.errors)
					resultsArea.append(
						$('<p class="text-danger"></p>').text(`${error.source}: ${error.error}`)
					);
				sessionStorage.removeItem(storageKey);
				invalidate();
				return;
			}
			if (state.status === "Failed") {
				resultsArea.append($('<p class="text-danger"></p>').text(state.error));
				sessionStorage.removeItem(storageKey);
				invalidate();
				return;
			}
			resultsArea.append(
				$("<p></p>").text(
					__("Import {0}. This page will update when the background worker finishes.", [
						state.status.toLowerCase(),
					])
				)
			);
			await new Promise((resolve) => setTimeout(resolve, 2500));
		}
	}
	page.add_inner_button(__("Check running import"), async () => {
		const token = sessionStorage.getItem(storageKey);
		if (!token || busy) return;
		setBusy(true);
		try {
			await monitor(token);
		} finally {
			setBusy(false);
		}
	});
	const previousJob = sessionStorage.getItem(storageKey);
	if (previousJob) {
		setBusy(true);
		monitor(previousJob).finally(() => setBusy(false));
	}
};
