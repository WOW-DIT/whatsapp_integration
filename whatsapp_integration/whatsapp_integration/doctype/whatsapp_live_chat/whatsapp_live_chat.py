# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from whatsapp_integration.whatsapp_api import send_message
from datetime import datetime, timedelta
import json


class WhatsAppLiveChat(Document):
	pass

@frappe.whitelist()
def start_live_session(chat_id):
	try:
		if frappe.db.exists(
			"Ai Chat",
			chat_id,
		):
			frappe.db.set_value(
				"Ai Chat",
				chat_id,
				"is_live",
				1,
				update_modified=False,
			)
			url = f"/app/whatsapp-live-chat/WhatsApp%20Live%20Chat?chat_id={chat_id}"
			return {"success": True, "url": url}
		
		return {"success": False, "error": "Chat not found"}
	except Exception as e:
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def end_live_session(chat_id):
	try:
		if frappe.db.exists(
			"Ai Chat",
			chat_id,
		):
			frappe.db.set_value(
				"Ai Chat",
				chat_id,
				"is_live",
				0,
				update_modified=False,
			)
			url = "/app"
			return {"success": True, "url": url}
		
		return {"success": False, "error": "Chat not found"}
	except Exception as e:
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_messages(chat_id, page=1):
	try:
		page_size = 50
		messages = frappe.get_list(
			"Ai Message",
			filters={"chat": chat_id, "response_type": "Normal"},
			fields=["name", "role", "type", "message_text", "image", "timestamp"],
			order_by="timestamp",
			limit=page_size * page,
		)
		return {"success": True, "messages": messages}
	
	except Exception as e:
		return {"success": True, "error": str(e)}
	

@frappe.whitelist()
def send_live_message(chat_id: str, message_type: str, text: str):
	try:
		chat = frappe.get_doc("Ai Chat", chat_id)
		# instance = frappe.get_doc("WhatsApp Instance", instance_id)
		client_number = chat.user_id

		response = send_message(
			phone_id=chat.phone_id,
			client_number=client_number,
			type=message_type,
			text=text,
		)

		success = response.status_code == 200

		if success:
			data = response.json()
			message = data["messages"][0]
			wam_id = message.get("id")
			role = frappe.session.user

			payload = {
				"type": "question",
				"response": text,
				"client_number": client_number,
			}

			msg = frappe.new_doc("Ai Message")
			msg.chat = chat_id
			msg.type = "text"
			msg.whatsapp_message_id = wam_id
			msg.role = role
			
			msg.content = json.dumps(payload, ensure_ascii=False)
			msg.message_text = text
			msg.timestamp = datetime.now()
			msg.insert(ignore_permissions=True)

			chat.append(
				"messages",
				{
					"role": msg.role,
					"message_text": msg.message_text,
					"content": msg.content,
				}
			)
			chat.save(ignore_permissions=True)
			
			return {"success": success}
		
		return {"success": success, "error": str(response.text)}
	
	except Exception as e:
		return {"success": False, "error": str(e)}