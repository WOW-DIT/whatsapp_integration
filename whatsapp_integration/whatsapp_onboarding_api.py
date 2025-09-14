import frappe
import requests
import base64

@frappe.whitelist(allow_guest=True)
def signup_webhook():
    pass

@frappe.whitelist(allow_guest=True)
def init_instance(code, phone_id, business_id, email=None):
    try:
        insts = frappe.get_all(
            "WhatsApp Instance",
            filters={"phone_id": phone_id, "business_id": business_id},
            fields=["name"]
        )

        if insts:
            instance = frappe.get_doc("WhatsApp Instance", insts[0].name)

        else:
            instance = frappe.new_doc("WhatsApp Instance")
            instance.phone_id = phone_id
            instance.business_id = business_id

            if email:
                instance.user = email

            instance.insert(ignore_permissions=True)

            user_perm = frappe.new_doc("User Permission")
            user_perm.user = frappe.session.user
            user_perm.allow = "WhatsApp Instance"
            user_perm.for_value = instance.name
            user_perm.insert(ignore_permissions=True)

            frappe.db.commit()

        return generate_token(code, instance)
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist(allow_guest=True)
def generate_token(code, instance):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    url = f"https://graph.facebook.com/{wa_settings.api_version}/oauth/access_token"
    request_data = {
        "client_id": wa_settings.app_id,
        "client_secret": wa_settings.get_password("app_secret"),
        "code": code,
        "grant_type": "authorization_code",
    }

    response = requests.post(url, json=request_data)
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()

        instance.token = data["access_token"]
        instance.save(ignore_permissions=True)
        frappe.db.commit()

        return {"token_content": str(response.json()), "instance_id": instance.name}
    else:
        raise Exception("failed")


@frappe.whitelist(allow_guest=True)
def register_phone_number(instance_id, pin):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
    instance = frappe.get_doc("WhatsApp Instance", instance_id)
    token = instance.get_password("token")

    url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.phone_id}/register"
    request_data = {
        "messaging_product": "whatsapp",
        "pin": pin,
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(url, json=request_data, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()
        success = data["success"]

        return {"success": success, "message": "WhatsApp phone number registered successfully."}        
    else:
        return {"success": False, "error": response.text}


@frappe.whitelist(allow_guest=True)
def subscribe_business_account(instance_id):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
    instance = frappe.get_doc("WhatsApp Instance", instance_id)
    token = instance.get_password("token")

    url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.business_id}/subscribed_apps"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(url, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        data = response.json()
        success = data["success"]

        return {"success": success, "message": "WABA has been subscribed successfully."}        
    else:
        return {"success": False, "error": response.text}
    

@frappe.whitelist(allow_guest=True)
def check_business_account_sub(instance_id):
    try:
        wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
        instance = frappe.get_doc("WhatsApp Instance", instance_id)
        token = instance.get_password("token")

        url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.business_id}/subscribed_apps"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            subs = response.json()["data"]
            is_subbed = False

            for sub in subs:
                app_id = sub["whatsapp_business_api_data"]["id"]
                if app_id == wa_settings.app_id:
                    is_subbed = True
                    break

            return {"success": is_subbed, "message": response.json()}      
        else:
            return {"success": False, "message": response.text}
    except Exception as e:
        return {"success": False, "message": str(e)}