# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class WhatsAppInstance(Document):
	pass

@frappe.whitelist()
def clear_chats(instance_id):
	try:
		chats = frappe.get_list(
			"Ai Chat",
			filters={"whatsapp_instance": instance_id},
			fields=["name", "channel_type", "whatsapp_instance"],
			limit=0,
		)

		deleted_chats = 0
		for chat in chats:
			frappe.set_value("Ai Chat", chat.name, "messages", [])

			channel_type = chat.channel_type
			if channel_type == "WhatsApp":
				filters = {
					"chat": chat.name,
					"channel_type": chat.channel_type,
					"whatsapp_instance": chat.whatsapp_instance,
				}
			elif channel_type == "Instagram":
				filters = {
					"chat": chat.name,
					"channel_type": chat.channel_type,
					"instagram_instance": chat.instagram_instance,
				}

			messages = frappe.get_list(
				"Ai Message",
				filters=filters,
				limit=0,
			)

			deleted_messages = 0
			for msg in messages:
				frappe.delete_doc_if_exists(
					"Ai Message",
					msg.name,
					force=1,
				)
				deleted_messages += 1
				

			frappe.delete_doc_if_exists(
				"Ai Chat",
				chat.name,
				force=1,
			)
			deleted_chats += 1

		return {"success": True, "message": f"({deleted_chats}) {_("Chats were deleted successfully. Total number of deleted messages")} ({deleted_messages})."}

	except Exception as e:
		return {"success": False, "error": str(e)}
