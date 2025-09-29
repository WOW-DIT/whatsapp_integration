# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class WhatsAppRegister(Document):
	def before_insert(self):
		self.validate_email()
		self.validate_business_name()

	def after_insert(self):
		self.create_whatsapp_user()
	
	
	def validate_email(self):
		if frappe.db.exists("User", self.email):
			frappe.throw(_("Email is already registered"))

	def validate_business_name(self):
		if frappe.db.exists("WhatsApp Business Account", {"business_display_name": str(self.business_name).strip()}):
			frappe.throw(_("Business display name is taken. Try another one."))

	def create_whatsapp_user(self):
		user = frappe.new_doc("User")
		user.email = self.email
		user.first_name = self.first_name
		user.last_name = self.last_name
		user.role_profile_name = "WhatsApp Signup User"
		user.module_profile = "WhatsApp Manager"
		user.send_welcome_email = 1
		user.insert(ignore_permissions=True)
		frappe.db.commit()
