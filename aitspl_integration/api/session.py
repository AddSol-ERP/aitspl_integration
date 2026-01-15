import frappe

@frappe.whitelist()
def check():
    if frappe.session.user == "Guest":
        return {
            "logged_in": False
        }

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user},
        ["name", "employee_name"],
        as_dict=True
    )

    return {
        "logged_in": True,
        "user": frappe.session.user,
        "employee": employee
    }
