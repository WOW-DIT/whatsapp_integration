import frappe
from werkzeug.wrappers import Response
from datetime import datetime
from ai_intergration.ai_intergration.api import ai_chat
import requests
import json

@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():
    if frappe.request.method == "GET":
        
        params = frappe.local.form_dict
        challenge = params.get("hub.challenge")
        verify_token = params.get("hub.verify_token")
        mode = params.get("hub.mode")

        instances = frappe.get_all(
            "WhatsApp Instance",
            filters={"verify_token": verify_token, "enabled": 1},
        )
        
        if mode == "subscribe" and instances:
            return Response(str(challenge), mimetype='text/plain')
        
    else:
        frappe.db.commit()
        try:
            import json
            raw_data = frappe.request.get_data(as_text=True)
            json_data = json.loads(raw_data)

            entry = json_data["entry"][0]
            business_id = entry["id"]
            phone_id = entry["changes"][0]["value"]["metadata"]["phone_number_id"]
            messages = entry["changes"][0]["value"]["messages"]

            wa_instances = frappe.get_all(
                "WhatsApp Instance",
                filters={"business_id": business_id, "enabled": 1},
                fields=["name", "business_id", "phone_id", "app_secret", "token"]
            )

            if not wa_instances:
                frappe.throw("Business user is not subscribed")

            wa_instance = wa_instances[0]
            token = wa_instance.token
                
            for msg in messages:
                to_number = entry["changes"][0]["value"]["contacts"][0]["wa_id"]
                from_number = msg["from"]
                timestamp = datetime.fromtimestamp(float(msg["timestamp"]))
                msg_body = msg["text"]["body"]

                log = frappe.new_doc("WhatsApp Logs")
                log.from_number = from_number
                log.to_number = to_number
                log.method = "Received"
                log.timestamp = timestamp
                log.body = msg_body
                log.save(ignore_permissions=True)

                try:
                    ai_response = respond_to_message(
                        business_id,
                        from_number,
                        msg_body,
                    )

                    if ai_response:
                        save_response_log(
                            ai_response,
                            from_number,
                            to_number,
                        )
                    wa_message = send_whatsapp_response(
                        phone_id=phone_id,
                        token=token,
                        to_number=to_number,
                        text=ai_response,
                    )

                except Exception as e:
                    save_response_log(
                        f"ERROR::::: {e}",
                        from_number,
                        to_number,
                    )

                    wa_message = send_whatsapp_response(
                        phone_id=phone_id,
                        token=token,
                        to_number=to_number,
                        text=str(e),
                    )
            
                    frappe.db.commit()

            frappe.db.commit()
                

            # optional: respond with a message
            return {"status": "success", "message": "Webhook received", "content": json_data}
        except Exception as e:
            log = frappe.new_doc("WhatsApp Logs")
            log.body = str(e)
            log.save(ignore_permissions=True)

def respond_to_message(business_id, from_number, text):
    ai_contexts = frappe.get_all(
        "Message Context Template",
        filters={"whatsapp_business_id": business_id},
        fields=["name", "llm", "gpt_model", "override_model"]
    )

    if not ai_contexts:
        return None

    ai_context = ai_contexts[0]

    chat = get_chat(
        business_id,
        from_number,
        ai_context,
    )

    ai_response = ai_chat(
        model=chat.model,
        chat_id=chat.name,
        new_message={
            "role": "user",
            "content": f"({from_number}) says: {text}",
        },
    ) 
    return ai_response


def get_chat(business_id, from_number, ai_context):
    chats = frappe.get_all(
        "Ai Chat",
        filters={
            "whatsapp_business_id": business_id,
            "whatsapp_client_id": from_number,
        },
        fields=["name", "model"]
    )

    if chats:
        chat = chats[0]
    else:
        chat = frappe.new_doc("Ai Chat")
        if ai_context.override_model == 1:
            chat.model = ai_context.gpt_model
        else:
            chat.model = ai_context.llm
        chat.context = ai_context.name
        chat.whatsapp_business_id = business_id
        chat.whatsapp_client_id = from_number
        chat.save(ignore_permissions=True)

        frappe.db.commit()

    return chat


def send_whatsapp_response(phone_id, token, to_number, text):
    url = f"https://graph.facebook.com/v22.0/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {
            "body": text
        }
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    save_response_log(
        str(response.json()),
        "6666666666666666666666666666666666666666666666666666666666666",
        to_number,
    )


def post_to_webhook(context):
    url = context.webhook_uri
    payload = json.loads(context.json_template)
    headers = {}

    if context.auth_token:
        headers["Authorization"] = context.auth_token

    tries = 3
    while tries > 0:
        response = requests.post(url=url, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            tries -= 1


def save_response_log(body, from_number, to_number):
    log = frappe.new_doc("WhatsApp Logs")
    log.from_number = from_number
    log.to_number = to_number
    log.method = "Sent"
    log.timestamp = datetime.now()
    log.body = body
    log.save(ignore_permissions=True)