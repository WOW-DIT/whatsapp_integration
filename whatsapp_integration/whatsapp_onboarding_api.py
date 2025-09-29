import frappe
import requests
import base64

@frappe.whitelist(allow_guest=True)
def signup_webhook():
    pass


def init_business_account(business_id, business_name):
    business_accounts = frappe.get_all(
        "WhatsApp Business Account",
        filters={"business_account_id": business_id},
        limit=1
    )
    
    if business_accounts:
        business_account = frappe.get_doc("WhatsApp Business Account", business_accounts[0].name)
    else:
        business_account = frappe.new_doc("WhatsApp Business Account")
        business_account.business_account_id = business_id
        business_account.business_display_name = business_name
        business_account.insert(ignore_permissions=True)

    return business_account


@frappe.whitelist(allow_guest=True)
def init_instance(code, phone_id, business_id, business_name, email=None):
    try:
        insts = frappe.get_all(
            "WhatsApp Instance",
            filters={"phone_id": phone_id, "business_id": business_id},
            fields=["name"]
        )

        if insts:
            instance = frappe.get_doc("WhatsApp Instance", insts[0].name)

        else:
            business_account = init_business_account(business_id, business_name)

            instance = frappe.new_doc("WhatsApp Instance")
            instance.phone_id = phone_id
            instance.business_account = business_account.name

            if email:
                instance.user = email

            instance.insert(ignore_permissions=True)

            set_user_permission(business_account.doctype,business_account.name)
            set_user_permission(instance.doctype, instance.name)

            user = frappe.get_doc("User", frappe.session.user)
            user.role_profile_name = "WhatsApp Manager"
            user.save(ignore_permissions=True)
            
            frappe.db.commit()

        return generate_token(code, instance)
    except Exception as e:
        return {"error": str(e)}


def set_user_permission(doctype, value):
    perm_exists = frappe.db.exists(
        "User Permission",
        {
            "user": frappe.session.user,
            "allow": doctype,
            "for_value": value
        }
    )
    if perm_exists:
        return
    
    user_perm = frappe.new_doc("User Permission")
    user_perm.user = frappe.session.user
    user_perm.allow = doctype
    user_perm.for_value = value
    user_perm.insert(ignore_permissions=True)


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
        raise Exception("Token generation failed")


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
        return {"success": False, "error": response.text, "status": response.status_code}


@frappe.whitelist(allow_guest=True)
def subscribe_business_account(instance_id):
    ## Get whatsapp settings (api_version, app_id, app_secret, etc...)
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    ## Client Number ID
    instance = frappe.get_doc("WhatsApp Instance", instance_id)
    business_account = frappe.get_doc("WhatsApp Business Account", instance.business_id)

    ## Client Number Token
    token = instance.get_password("token")

    ## API endpoint
    url = f"https://graph.facebook.com/{wa_settings.api_version}/{instance.business_id}/subscribed_apps"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    ## Send Request to API
    response = requests.post(url, headers=headers)

    ## response.status_code == 200 -> Success
    ## response.status_code != 200 -> Failure
    if response.status_code == 200 or response.status_code == 201:
        ## Response Data
        data = response.json()
        
        success = data["success"]

        business_account.active = 1
        business_account.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": success, "message": "WABA has been subscribed successfully."}        
    else:
        return {"success": False, "error": response.text}
    

@frappe.whitelist(allow_guest=True)
def check_business_account_sub(instance_id):
    try:
        wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
        instance = frappe.get_doc("WhatsApp Instance", instance_id)
        business_account = frappe.get_doc("WhatsApp Business Account", instance.business_account)
        token = instance.get_password("token")

        if not business_account.active:
            return {"success": False, "message": "WhatsApp Business Account is not active"}
        
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