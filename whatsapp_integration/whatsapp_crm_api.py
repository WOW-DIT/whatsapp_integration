import frappe
import json
import requests


@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_customer(mobile_number, customer_name, email=None, gender=None, national_id=None, test=False):
    if test:
        return None
        
    if not frappe.db.exists("Ai Chat", {"user_id": mobile_number}):
        frappe.response["message"] = {"success": False, "error": "Chat not found"}
        
    else:
        if frappe.db.exists("Customer", {"email_id": email, "mobile_no": mobile_number}):
            frappe.response["message"] = {"success": False, "error": "Customer already exists."}
        
        try:
            customer = frappe.new_doc("Customer")
            customer.customer_name = customer_name
            customer.customer_type = "Individual"
            customer.email_id = email
            customer.mobile_no = mobile_number
            customer.gender = gender
            customer.tax_id = national_id
            customer.insert(ignore_permissions=True)
            
            frappe.response["message"] = {"success": True, "message": "Customer registered successfully"}
        
        except Exception as e:
            frappe.response["message"] = {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def check_customer(mobile_number, test=False):
    if test:
        return None

    customers = frappe.get_all("Customer", filters={"mobile_no": mobile_number}, limit=1)

    if customers:
        customer = frappe.get_doc("Customer", customers[0].name)
        frappe.response["customer"] = {
            "full_name": customer.customer_name,
            "mobile_number": customer.mobile_no,
            # "email": customer.email_id,
            "national_id": customer.tax_id,
        }
        return
    
    frappe.response["customer"] = "Customer not found"

@frappe.whitelist(allow_guest=True, methods=["POST"])
def add_ticket(client_number, subject, issue_type, description, test=False):
    if test:
        return None
    
    try:
        customers = frappe.get_all("Customer", filters={"mobile_no": client_number})
        if not customers:
            frappe.response["success"] = False
            frappe.response["error"] = "Customer not found"
            return None
        
        customer = frappe.get_doc("Customer", customers[0].name)
        ticket = frappe.new_doc("Issue")
        ticket.subject = subject
        ticket.issue_type = issue_type
        ticket.description = description
        ticket.customer = customer
        ticket.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.response["success"] = True
        frappe.response["message"] = "Ticket submitted successfully"

    except Exception as e:
        frappe.response["success"] = False
        frappe.response["error"] = str(e)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def issue_types():
    frappe.response["issue_types"] = frappe.get_all("Issue Type")