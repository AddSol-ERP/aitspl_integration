import frappe
from frappe.auth import LoginManager

@frappe.whitelist(allow_guest=True)
def employee_login(employee_id):
    if not employee_id:
        frappe.throw("Employee ID is required")

    employee = frappe.db.get_value(
        "Employee",
        employee_id,
        ["user_id", "status"],
        as_dict=True
    )

    if not employee:
        frappe.throw("Invalid Employee ID")

    if employee.status != "Active":
        frappe.throw("Employee is not active")

    if not employee.user_id:
        frappe.throw("Employee not linked to a system user")

    # ✅ CORRECT: password-less login
    lm = LoginManager()
    lm.login_as(employee.user_id)

    return {
        "status": "success",
        "user": employee.user_id,
        "employee": employee_id
    }
