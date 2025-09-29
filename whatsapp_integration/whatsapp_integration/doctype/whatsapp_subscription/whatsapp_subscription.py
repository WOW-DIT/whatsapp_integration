# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WhatsAppSubscription(Document):
	pass

@frappe.whitelist()
def toggle_activity(sub_id, active):
	sub = frappe.get_doc("WhatsApp Subscription", sub_id)
	sub.enabled = active
	sub.save(ignore_permissions=True)
