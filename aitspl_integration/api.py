import frappe

@frappe.whitelist()
def get_biometric_integration():
    """Return data from single doctype + its child table."""
    doc = frappe.get_single("Biometric Integration")
    # manually fetch child table rows
    devices = frappe.get_all(
        "Biometric Device",
        filters={"parent": "Biometric Integration"},
        fields=["device_name", "ip_address", "port", "status"]
    )
    return {
        "devices": devices
    }
