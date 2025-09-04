# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url
import requests
from whatsapp_integration.whatsapp_api import upload_media, get_mime_type, upload_file_full
import re

class WhatsAppMessageTemplate(Document):
	def validate(self):
		self.validate_header_parameters()
		self.validate_body_parameters()
		self.sync_template()

	def validate_header_parameters(self):
		if self.header_format == "TEXT":
			template = self.header_text
			compare_text = self.header_examples

			# 1. Find all placeholders like {{1}}, {{2}}
			matches = re.findall(r"{{(\d+)}}", template)
			
			# 2. Check uniqueness
			if len(matches) != len(set(matches)):
				frappe.throw("Duplicate parameters found in 'Header'")
			
			# 3. Count placeholders
			placeholder_count = len(matches)
			
			# 4. Count parts in compare_text
			parts = compare_text.split("|")
			if len(parts) != placeholder_count:
				frappe.throw("Mismatch in number of parameters in 'Header'")
			
	def validate_body_parameters(self):
		template = self.body
		compare_text = self.body_examples

		# 1. Find all placeholders like {{1}}, {{2}}
		matches = re.findall(r"{{(\d+)}}", template)
		
		# 2. Check uniqueness
		if len(matches) != len(set(matches)):
			frappe.throw("Duplicate parameters found in 'Body'")
		
		# 3. Count placeholders
		placeholder_count = len(matches)
		
		# 4. Count parts in compare_text
		parts = compare_text.split("|")
		if len(parts) != placeholder_count:
			frappe.throw("Mismatch in number of parameters in 'Body'")


	def sync_template(self):
		try:
			wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
			instance = frappe.get_doc("WhatsApp Instance", self.instance)
			
			api_version = wa_settings.api_version
			app_id = wa_settings.app_id
			token = instance.get_password("token")
			phone_id = instance.phone_id
			business_id = instance.business_id

			self.api_endpoint = f"https://graph.facebook.com/{wa_settings.api_version}/{business_id}/message_templates"
			try:
				self.components = self.build_components(
					api_version,
					app_id,
					token,
				)
			except Exception as e:
				frappe.throw(str(e))

			if self.status == "NEW":
				response = self.create_template(wa_settings.time_to_live, token)
			else:
				response = self.update_template(api_version, token)

			if not response["success"]:

				error_msg = response.get("message")
				if isinstance(error_msg, dict):

					error_msg = error_msg.get("error", {}).get("message") or str(error_msg)
				self.log = response

				frappe.msgprint(error_msg)

		except Exception as e:
			frappe.throw(str(e))

		
	def build_components(self, api_version, app_id, token):
		header = {
			"type": "HEADER",
			"format": self.header_format,
		}
		if self.header_format == "TEXT":
			header["text"] = self.header_text
			examples = [str(e).strip() for e in str(self.header_examples).split("|") if e.strip()]
			header["example"] = {
				"header_text": [examples]
			}
		else:
			# file_url = f"{get_url()}{self.header_example_file}"
			
			file_doc = frappe.get_doc("File", {"file_url": self.header_example_file})
			local_path = file_doc.get_full_path()

			file_extension = local_path.split(".")[-1]
			mime_type = get_mime_type(file_extension)


			""" GET DOCUMENT HANDLE """
			if self.document_handle_id:
				media_handle = self.document_handle_id
			else:
				media_handle = upload_file_full(
					api_version,
					app_id,
					token,
					local_path,
					mime_type,
				)
				self.document_handle_id = media_handle

			header["example"] = {
				"header_handle": [
					media_handle
				]
			}

		components = [
			header,
			{
				"type": "BODY",
				"text": self.body,
				"example": {
					"body_text": [
						str(self.body_examples).split("|")
					]
				}
			},
			{
				"type": "FOOTER",
				"text": self.footer
			}
		]
		return components
	
	
	def create_template(self, time_to_live, token):
		try:
			body = {
				"name": self.template_name,
				"category": self.category,
				# "message_send_ttl_seconds": time_to_live,
				# "parameter_format": self.parameter_format,
				"language": self.language,
				"components": self.components
			}

			headers = {
				"Authorization": f"Bearer {token}"
			}

			response = requests.post(self.api_endpoint, json=body, headers=headers)

			if response.status_code == 200:
				data = response.json()

				self.template_id = data["id"]
				self.status = data["status"]

				frappe.msgprint("Template is created and being under review.\n Check the status later.")
				return {"success": True, "message": response.json(), "body": str(body)}
			
			else:
				return {"success": False, "message": response.json(), "body": str(body)}
		except Exception as e:
			return {"success": False, "message": str(e)}
		

	def update_template(self, api_version, token):
		try:
			body = {
				"category": self.category,
				"components": self.components
			}

			headers = {
				"Authorization": f"Bearer {token}"
			}
			
			url = f"https://graph.facebook.com/{api_version}/{self.template_id}"
			response = requests.post(url, json=body, headers=headers)

			if response.status_code == 200:
				data = response.json()

				frappe.msgprint("Template is updated successfully.")
				return {"success": data["success"], "message": response.json(), "body": str(body)}
			
			else:
				return {"success": False, "message": response.json(), "body": str(body)}
		except Exception as e:
			return {"success": False, "message": str(e)}