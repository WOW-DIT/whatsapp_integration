# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from whatsapp_integration.whatsapp_api import send_message

class WhatsAppBroadcastMessage(Document):
	def on_submit(self):
		if self.workflow_state == "Sent":
			self.send_wa_message()

	def send_wa_message(self):
		instance = frappe.get_doc("WhatsApp Instance", self.whatsapp_instance)
		template_name = None
		template_langauge = None
		template_components = None
		
		if self.message_type.lower() == "template":
			template = frappe.get_doc("WhatsApp Message Template", self.template)
			template_name = template.template_name
			template_langauge = template.language
			template_components = self.compose_components()

			self.error_message = str(template_components)

		for client in self.numbers:
			try:
				response = send_message(
					phone_id=instance.phone_id,
					client_number=client.number,
					type=self.message_type.lower(),
					text=self.text,
					template_name=template_name,
					template_language=template_langauge,
					template_components=template_components,
				)
				if response.status_code != 200:
					self.append(
						"error_logs",
						{
							"number": client.number, "error": response.text,
						}
					)
			except Exception as e:
				self.append(
					"error_logs",
					{
						"number": client.number, "error": str(e),
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



@frappe.whitelist()
def send_wa_message(bc_id):
	bc = frappe.get_doc("WhatsApp Broadcast Message", bc_id)
	template = frappe.get_doc("WhatsApp Message Template", bc.template)
	header_type = template.header_type

	if header_type == "TEXT":
		pass
	else:
		extension = template.header_example_file.split(".")[-1]
		f_type = file_type(extension)


def file_type(extension):
	types = {
		"png": "image",
		"jpg": "image",
		"jpeg": "image",
		"pdf": "pdf",
	}
	return types[extension]
