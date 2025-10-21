# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from whatsapp_integration.whatsapp_api import send_message
import json
import pandas as pd
from frappe.utils.file_manager import get_file_path

class WhatsAppBroadcastMessage(Document):
	def on_submit(self):
		if self.workflow_state == "Sent":
			send_bulk_messages(self.name)
	
	
def send_bulk_messages(reference_id):
	self = frappe.get_doc("WhatsApp Broadcast Message", reference_id)
	instance = frappe.get_doc("WhatsApp Instance", self.whatsapp_instance)
	template_name = None
	template_langauge = None
	template_components = None
	latitude =None
	longitude=None
	address=None
	location_name=None
	image_url=None
	image_caption=None

	
	if self.message_type.lower() == "template":
		template = frappe.get_doc("WhatsApp Message Template", self.template)
		template_name = template.template_name
		template_langauge = template.language
		template_components = compose_components(self)

		self.error_message = str(template_components)

	if self.message_type.lower() == "location":
		coords = json.loads(self.location)["features"][0]["geometry"]["coordinates"]
		latitude = str(coords[0])
		longitude = str(coords[1])
		location_name = self.location_name
		address = self.address

	if self.message_type.lower() == "image":			
		image_url=self.image
		image_caption=self.image_caption

	numbers = [client.number for client in self.numbers if client.number]

	if self.numbers_source == "Excel" and self.file:
		file_path = get_file_path(self.file)
		try:
			df = pd.read_excel(file_path)
			if 'number' in df.columns:
				excel_numbers = df['number'].dropna().astype(str).tolist()
				numbers.extend(excel_numbers)
		except Exception as e:
			frappe.throw(f"Error reading Excel file: {e}")

	numbers = list(set(numbers))

	for number in numbers:
		try:
			response = send_message(
				phone_id=instance.phone_id,
				client_number=number,
				type=self.message_type.lower(),
				text=self.text,
				template_name=template_name,
				template_language=template_langauge,
				template_components=template_components,
				latitude = latitude,
				longitude =longitude,
				location_name=location_name,
				address=address,
				image_url=image_url,
				image_caption=image_caption,
			)
			if response.status_code != 200:
				frappe.throw(str(response.text))

				self.append(
					"error_logs",
					{
						"number": number, "error": response.text,
					}
				)

			return response
			
		except Exception as e:
			frappe.throw(str(e))
			self.append(
				"error_logs",
				{
					"number": number, "error": str(e),
				}
			)

		
def compose_components(self):
	components = []

	## Header Parameters
	header_components = frappe.get_all(
		"Message Components Table",
		filters={"parent": self.name, "section_name": "header"},
		fields=["type", "text", "file_url", "file_name"],
		order_by="param_order",
	)
	if header_components:
		components.append({"type": "header", "parameters": []})
		header_params = components[0]["parameters"]
		
		for c in header_components:
			param = {"type": c.type}

			if c.type == "text":
				param["text"] = c.text

			elif c.type == "image":
				param["image"] = {"link": c.file_url}

			elif c.type == "document":
				param["document"] = {
					"link": c.file_url,
					"filename": c.file_name,
				}

			else:
				frappe.throw("Header parameter type must be one of: text, image, document")

			header_params.append(param)


	## Body parameters
	body_components = frappe.get_all(
		"Message Components Table",
		filters={"parent": self.name, "section_name": "body"},
		fields=["type", "text"],
		order_by="param_order",
	)
	if body_components:
		body_comp = {"type": "body", "parameters": []}
		body_params = body_comp["parameters"]

		for c in body_components:
			if c.type != "text":
				frappe.throw("Body parameters must be type 'text' to match {{n}} placeholders.")

			body_params.append({
				"type": c.type,
				"text": c.text,
			})
		components.append(body_comp)


	## Buttons parameters
	button_components = frappe.get_all(
		"Message Components Table",
		filters={"parent": self.name, "section_name": "button"},
		fields=["type", "sub_type", "text"],
		order_by="param_order",
	)
	for idx, c in enumerate(button_components):
		button_comp = {
			"type": "button",
			"sub_type": c.sub_type,
			"index": str(idx),
			"parameters": [],
		}
		button_params = button_comp["parameters"]

		if c.sub_type == "url":
			button_params.append({
				"type": "text",
				"text": c.text,
			})

		components.append(body_comp)

	return components


@frappe.whitelist(methods=["POST"], allow_guest=True)
def init_broadcast(
	instance_id: str,
	numbers: list[str],
	message_type: str,
	text: str=None,
	template_name: str=None,
	components: list=None,
	save_context: bool=False,
):
	m_broadcast = frappe.new_doc("WhatsApp Broadcast Message")
	m_broadcast.numbers_source = "Manually"
	m_broadcast.whatsapp_instance = instance_id
	m_broadcast.save_context = save_context
	m_broadcast.message_type = message_type.lower()

	if message_type.lower() == "text":
		m_broadcast.text = text

	elif message_type.lower() == "template":
		template = frappe.get_all(
			"WhatsApp Message Template",
			filters={"instance": instance_id, "template_name": template_name},
		)
		if not template:
			frappe.throw(f"Template {template_name} was not found")
			
		template = template[0]
		m_broadcast.template = template.name

		if components:
			for c in components:
				section_name = c.get("section_name")
				params = c.get("params")
				
				for i, p in enumerate(params):
					param_type = p.get("type")

					new_component = {
						"section_name": section_name,
						"param_order": i+1,
						"type": param_type,
					}
					if param_type == "text":
						param_text = p.get("text")
						new_component["text"] = param_text

					elif param_type == "image":
						file_url = p.get("file_url")
						new_component["file_url"] = file_url

					elif param_type == "document":
						file_url = p.get("file_url")
						file_name = p.get("file_name")
						new_component["file_url"] = file_url
						new_component["file_name"] = file_name

					elif param_type == "button":
						sub_type = p.get("sub_type")
						file_path = p.get("file_path")
						new_component["sub_type"] = sub_type
						new_component["text"] = file_path

					m_broadcast.append(
						"components",
						new_component
					)

	for number in numbers:
		m_broadcast.append(
			"numbers",
			{"number": number}
		)

	m_broadcast.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"success": True,
		"reference_id": m_broadcast.name,
		"message": "Message draft has been created",
	}

@frappe.whitelist(allow_guest=True)
def submit_broadcast(reference_id):
	response = send_bulk_messages(reference_id)
	
	# if response.status_code == 200:
	# 	broadcast = frappe.get_doc("WhatsApp Broadcast Message", reference_id)
	# 	broadcast.submit()

	return response


def file_type(extension):
	types = {
		"png": "image",
		"jpg": "image",
		"jpeg": "image",
		"pdf": "pdf",
	}
	return types[extension]
