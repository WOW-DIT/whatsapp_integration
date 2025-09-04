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
            frappe.db.commit()

        return generate_token(code, instance)
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist(allow_guest=True)
def generate_token(code, instance):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    request_data = {
        "client_id": wa_settings.app_id,
        "client_secret": wa_settings.get_password("app_secret"),
        "code": code,
        "grant_type": "authorization_code",
        # "redirect_uri": "https://whatsapp.wowdigital.sa/wa_signup/"
    }
    url = f"https://graph.facebook.com/{wa_settings.api_version}/oauth/access_token"
    response = requests.post(url, json=request_data)

    if response.status_code == 200 or response.status_code == 201:
        data = response.json()

        instance.enabled = 1
        instance.token = data["access_token"]
        instance.save(ignore_permissions=True)
        frappe.db.commit()

        return {"token_content": str(response.json())}
    else:
        raise Exception("failed")