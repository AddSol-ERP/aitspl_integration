import frappe, os, json

def after_install():
    fixtures_root = frappe.get_app_path("aitspl_integration", "aitspl_integration", "fixtures")

    for root, dirs, files in os.walk(fixtures_root):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                frappe.logger().info(f"Applying fixture: {file_path}")

                try:
                    with open(file_path) as f:
                        data = json.load(f)

                    for d in data:
                        if d.get("doctype") == "Custom Field":
                            exists = frappe.db.exists("Custom Field", {"dt": d["dt"], "fieldname": d["fieldname"]})
                            if exists:
                                frappe.logger().info(f"Skipping existing field: {d['dt']} -> {d['fieldname']}")
                                continue

                        frappe.get_doc(d).insert(ignore_permissions=True)
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Fixture import failed: {file[:140]}")
                    frappe.throw(f"Failed to load fixture from {file_path}: {str(e)}")
