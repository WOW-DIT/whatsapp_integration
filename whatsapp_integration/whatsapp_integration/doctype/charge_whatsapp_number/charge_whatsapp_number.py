# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ChargeWhatsAppNumber(Document):
	def on_submit(self):
		add_balance(self.business_account, self.user, self.number_of_messages, "add")


def get_subscription(whatsapp_business_account, user) -> Document:
	subs = frappe.get_all(
		"WhatsApp Subscription",
		filters={"business_account": whatsapp_business_account}
	)

	if subs:
		sub = frappe.get_doc("WhatsApp Subscription", subs[0].name)
	else:
		sub = frappe.new_doc("WhatsApp Subscription")
		sub.user = user
		sub.business_account = whatsapp_business_account
		sub.insert(ignore_permissions=True)

	return sub

@frappe.whitelist()
def add_balance(whatsapp_business_account, user, number_of_messages: int, charge_method: str="replace"):
	sub = get_subscription(whatsapp_business_account, user)

	if charge_method == "add":
		if sub.balance is None:
			sub.balance = 0
		sub.balance += number_of_messages

	elif charge_method == "replace":
		sub.balance = number_of_messages

	sub.save(ignore_permissions=True)
	frappe.db.commit()