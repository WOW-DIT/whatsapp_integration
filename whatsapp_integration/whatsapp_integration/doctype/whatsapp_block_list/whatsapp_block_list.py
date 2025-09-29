# Copyright (c) 2025, Mosaab Bleik and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests


class WhatsAppBlockList(Document):
     def before_insert(self):
            resp = block_users(self.whatsapp_instance, self.phone_number)
            if not resp["success"]:
                 frappe.throw(resp["error"])
               
     def on_trash(self):
            unblock_users(self.whatsapp_instance, self.phone_number)

@frappe.whitelist()
def block_users(instance_id, number):
    ## Get whatsapp settings (api_version, app_id, app_secret, etc...)
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    ## Client Number ID
    instance = frappe.get_doc("WhatsApp Instance", instance_id)

    ## Client Number Token
    token = instance.get_password("token")

    ## API endpoint
    url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.phone_id}/block_users"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
		"messaging_product": "whatsapp",
		"block_users": [
			{
				"user": number
			}  
		]
	}
    

    ## Send Request to API
    response = requests.post(url, headers=headers, json=payload)

    ## response.status_code == 200 -> Success
    ## response.status_code != 200 -> Failure
    if response.status_code == 200:
        return {"success": True, "message": "WABA has been subscribed successfully."}        
    else:
        data = response.json()
        error = data["error"]["error_data"]["details"]
        return {"success": False, "error": error}
    

@frappe.whitelist()
def unblock_users(instance_id, number):
    ## Get whatsapp settings (api_version, app_id, app_secret, etc...)
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    ## Client Number ID
    instance = frappe.get_doc("WhatsApp Instance", instance_id)

    ## Client Number Token
    token = instance.get_password("token")

    ## API endpoint
    url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.phone_id}/block_users"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
		"messaging_product": "whatsapp",
		"block_users": [
			{
				"user": number
			}  
		]
	}
    

    ## Send Request to API
    response = requests.delete(url, headers=headers, json=payload)

    ## response.status_code == 200 -> Success
    ## response.status_code != 200 -> Failure
    if response.status_code == 200:
        return {"success": True, "message": "WABA has been subscribed successfully."}        
    else:
        data = response.json()
        error = data["error"]["error_data"]["details"]
        return {"success": False, "error": error}
    