import frappe
from werkzeug.wrappers import Response
from datetime import datetime
from ai_intergration.ai_intergration.api import ai_chat, speech_to_text
import requests
import json
from io import BytesIO
import uuid
import os

@frappe.whitelist(allow_guest=True)
def get_wa_token(phone_id):
    instance = frappe.get_all("WhatsApp Instance", filters={"phone_id": phone_id})
    instance = frappe.get_doc("WhatsApp Instance", instance[0].name)
    return instance.get_password("token")


@frappe.whitelist()
def send_message(
    phone_id,
    client_number,
    type="text",
    text=None,
    template_name=None,
    template_language=None,
    template_components=None,
):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")

    instance = frappe.get_all("WhatsApp Instance", filters={"phone_id": phone_id})
    if not instance:
        frappe.response["status"] == 404

        return {"success": False, "message": "WhatsApp number id is not found"}
    
    instance = frappe.get_doc("WhatsApp Instance", instance[0].name)
    token = instance.get_password("token")
    api_version = wa_settings.api_version

    if type == "text":
        response = send_whatsapp_response(
            version=api_version,
            phone_id=phone_id,
            token=token,
            to_number=client_number,
            text=text,
        )
        
    elif type == "template":
        response = send_whatsapp_template(
            version=api_version,
            phone_id=phone_id,
            token=token,
            to_number=client_number,
            template_name=template_name,
            language_code=template_language,
            components=template_components,
        )        

    return response



@frappe.whitelist(allow_guest=True)
def whatsapp_webhook():
    if frappe.request.method == "GET":
        
        params = frappe.local.form_dict
        challenge = params.get("hub.challenge")
        verify_token = params.get("hub.verify_token")
        mode = params.get("hub.mode")

        wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
        
        if mode == "subscribe" and wa_settings.get_password("verify_token") == verify_token:
            return Response(str(challenge), mimetype='text/plain')
        
    else:
        try:
            raw_data = frappe.request.get_data(as_text=True)
            json_data = json.loads(raw_data)

            entry = json_data["entry"][0]
            business_id = entry["id"]
            changes = entry.get("changes", [])

            for change in changes:
                field = change.get("field")
                value = change.get("value")

                ## Update template status
                if field == "message_template_status_update":
                    try:
                        save_response_log(str(value), "lklklklklklklklkkl", "lklklklklklklklkkl")
                        template_id = value.get("message_template_id")
                        status = value.get("event")

                        update_template(str(template_id), str(status))
                    except:
                        continue
                    finally:
                        continue
                

                phone_id = value["metadata"]["phone_number_id"]
                messages = value.get("messages")

                if messages:
                    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
                    api_version = wa_settings.api_version

                    wa_instances = frappe.get_all(
                        "WhatsApp Instance",
                        filters={"business_id": business_id, "enabled": 1},
                        fields=[
                            "name", "user", "business_id",
                            "phone_id", "app_secret", "token",
                            "error_message",
                        ]
                    )
                    if not wa_instances:
                        raise Exception("Business user is not subscribed")

                    context = frappe.get_all(
                        "Message Context Template",
                        filters={"phone_id": phone_id},
                        fields=["name", "client_credentials", "override_model"],
                        limit=1,
                    )
                    if not context:
                        raise Exception("WhatsApp Ai Agent was not found")

                    context = context[0]
                    wa_instance = frappe.get_doc("WhatsApp Instance", wa_instances[0].name)
                    user = wa_instance.user
                    token = wa_instance.get_password("token")
                    
                    from_number = messages[0]["from"]
                    to_number = value["contacts"][0]["wa_id"]

                    try:
                        client_subscription = get_sub(user)
                        if client_subscription is None:
                            error_message = str(wa_instance.error_message).strip() if wa_instance.error_message else ""
                            if error_message:
                                raise Exception(error_message)
                            else:
                                return

                        for msg in messages:
                            timestamp = datetime.fromtimestamp(float(msg["timestamp"]))
                            message_type = msg["type"]
                            image = None

                            save_response_log(
                                str(msg),
                                "message",
                                "message",
                            )
                            if message_type == "text":
                                msg_body = msg["text"]["body"]
                            
                            elif message_type == "audio":
                                stt_error = wa_settings.stt_error_message
                                stt_model = wa_settings.stt_model
                                
                                try:
                                    if wa_settings.allow_stt == 0:
                                        raise Exception("1")
                                    
                                    media = msg["audio"]
                                    media_id = media.get("id")
                                    mime_type = media.get("mime_type")
                                    file = download_media(
                                        api_version,
                                        token,
                                        mime_type,
                                        media_id,
                                    )

                                    if file.get("error"):
                                        save_response_log(
                                            str(file),
                                            ";';';';';';'",
                                            ";';';';';';'",
                                            True
                                        )
                                
                                    file_content = file.get("content")
                                    file_name = file.get("name")

                                    if not file_content:
                                        raise Exception("2")
                                    
                                    if context.override_model == 0:
                                        raise Exception("3")
                                    
                                    msg_body = speech_to_text(
                                        stt_model,
                                        context.client_credentials,
                                        file_name,
                                        file_content,
                                    )
                                        
                                except Exception as e:
                                    wa_message = send_whatsapp_response(
                                        version=api_version,
                                        phone_id=phone_id,
                                        token=token,
                                        to_number=to_number,
                                        text=f"{stt_error}: {e}",
                                    )
                                    return

                            elif message_type == "image":
                                try:
                                    if context.override_model == 0:
                                        raise Exception("Sending images are currently not supported")
                                    
                                    media = msg["image"]
                                    media_id = media.get("id")
                                    mime_type = media.get("mime_type")
                                    caption = media.get("caption", "")
                                    msg_body = caption
                                    
                                    file = download_media(
                                        api_version,
                                        token,
                                        mime_type,
                                        media_id,
                                    )

                                    if file.get("error"):
                                        save_response_log(
                                            str(file),
                                            ";';';';';';'",
                                            ";';';';';';'",
                                            True
                                        )
                                
                                    image = file
                                    file_content = file.get("content")
                                    file_name = file.get("name")

                                except Exception as e:
                                    wa_message = send_whatsapp_response(
                                        version=api_version,
                                        phone_id=phone_id,
                                        token=token,
                                        to_number=to_number,
                                        text=f"image error: {e}",
                                    )
                                    return
                            else:
                                return

                            from_number = msg["from"]

                            log = frappe.new_doc("WhatsApp Logs")
                            log.from_number = from_number
                            log.to_number = to_number
                            log.method = "Received"
                            log.timestamp = timestamp
                            log.body = msg_body
                            log.save(ignore_permissions=True)

                            try:
                                ai_response = send_to_ai(
                                    wa_instance.name,
                                    from_number,
                                    to_number,
                                    message_type,
                                    msg_body,
                                    image,
                                    timestamp,
                                )

                                is_live = ai_response.get("is_live")
                                response_text = ai_response.get("response")
                                chat_id = ai_response.get("chat_id")

                                if is_live and ai_response:
                                    frappe.publish_realtime(
                                        f"whatsapp_chat_{chat_id}",
                                        message={"message": response_text, "sender": from_number}
                                    )

                                elif response_text:
                                    save_response_log(
                                        response_text,
                                        from_number,
                                        to_number,
                                    )
                                    wa_message = send_whatsapp_response(
                                        version=api_version,
                                        phone_id=phone_id,
                                        token=token,
                                        to_number=to_number,
                                        text=response_text,
                                    )

                            except Exception as e:
                                save_response_log(
                                    f"ERROR: {e}",
                                    from_number,
                                    to_number,
                                    True,
                                )

                                wa_message = send_whatsapp_response(
                                    version=api_version,
                                    phone_id=phone_id,
                                    token=token,
                                    to_number=to_number,
                                    text=str(e),
                                )
                        
                                frappe.db.commit()

                        frappe.db.commit()
                        return {"status": "success", "message": "Webhook received", "content": json_data}

                    except Exception as e:
                        send_whatsapp_response(
                            version=api_version,
                            phone_id=phone_id,
                            token=token,
                            to_number=to_number,
                            text=str(e),
                        )
                        return None
                

        except Exception as e:
            save_response_log(
                str(e),
                "--------",
                "--------",
                True,
            )
            return None


def update_template(template_id: str, status: str):
    try:
        templates = frappe.get_all(
            "WhatsApp Message Template",
            filters={"template_id": template_id}
        )
        if templates:
            template = frappe.get_doc("WhatsApp Message Template", templates[0].name)
            template.status = status
            template.save(ignore_permissions=True)
            frappe.db.commit()
            
    except Exception as e:
        save_response_log(
            str(e),
            "------",
            "------",
            True
        )



def get_mime_type(extension):
    types = {
        "aac": "audio/aac",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "txt": "text/plain",
        "pdf": "application/pdf",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "jpeg": "image/jpeg",
        "jpg": "image/jpg",
        "png": "image/png",
    }
    return types[extension]


def upload_media(api_version, token, phone_id, file_url, mime_type) -> dict:
    try:
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/media"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        # body = {
        #     "file": file_url,
        #     "type": mime_type,
        #     "messaging_product": "whatsapp",
        # }
        files = {
            "file": (file_url.split("/")[-1], open("/home/frappe/frappe-bench/sites/whatsapp.wowdigital.sa/public/files/redwsaczx.pdf", "rb"), mime_type),
            "messaging_product": (None, "whatsapp")
        }

        response = requests.post(url, headers=headers, files=files)
        
        # response = requests.post(url, json=body, headers=headers)

        data = response.json()

        return data
    
    except Exception as e:
        return {"error": str(e)}
    

def download_media(api_version, token, mime_type, media_id):
    try:
        type, file_extension = mime_type.split(";")[0].split("/")
        file_name = f"{uuid.uuid4()}.{file_extension}"

        url = f"https://graph.facebook.com/{api_version}/{media_id}/"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(url, headers=headers)

        data = response.json()
        media_url = data["url"]

        file_res = requests.get(media_url, headers=headers)
        file = None

        if file_res.status_code == 200:
            file_data = file_res.content

            file = BytesIO(file_data)

        return {"name": file_name, "type": type, "extension": file_extension, "content": file}
    
    except Exception as e:
        return {"error": str(e)}


def start_upload_session(
        api_version: str,
        app_id: str,
        access_token: str,
        file_path: str,
        file_type: str,
    ) -> str:
    """
    Start an upload session for a file.
    Returns the upload session ID (prefixed with 'upload:').
    """
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    url = f"https://graph.facebook.com/{api_version}/{app_id}/uploads"
    params = {
        "file_name": file_name,
        "file_length": file_size,
        "file_type": file_type,
        "access_token": access_token,
    }
    # headers = {"Authorization": f"Bearer {access_token}"}

    resp = requests.post(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    return data["id"]


def upload_file_chunk(api_version: str, upload_id: str, access_token: str, file_path: str, offset: int = 0) -> dict:
    """
    Upload a file (or chunk) to an existing session.
    Returns JSON response, which may include {"h": "<file_handle>"} when complete.
    """
    url = f"https://graph.facebook.com/{api_version}/{upload_id}"
    headers = {
        "Authorization": f"OAuth {access_token}",
        "file_offset": str(offset)
    }

    with open(file_path, "rb") as f:
        f.seek(offset)
        resp = requests.post(url, headers=headers, data=f)
        resp.raise_for_status()
        return resp.json()


def upload_file_full(api_version: str, app_id: str, access_token: str, file_path: str, file_type: str) -> str:
    """
    Helper: for small files (<25MB). Starts a session and uploads whole file.
    Returns the file handle ('h').
    """
    upload_id = start_upload_session(api_version, app_id, access_token, file_path, file_type)
    result = upload_file_chunk(api_version, upload_id, access_token, file_path, offset=0)
    if "h" not in result:
        raise RuntimeError(f"Upload did not return handle: {result}")
    return result["h"]


def get_sub(user):
    try:
        # today = datetime.now().date()
        # today_str = today.strftime("%Y-%m-%d")

        subs = frappe.get_all(
            "WhatsApp Subscription",
            filters={"user": user, "enabled": 1},
            fields=["name"],
            limit=1,
        )
        if subs:
            sub = frappe.get_doc("WhatsApp Subscription", subs[0].name)
            return sub
        
        return None
    except:
        return None


def send_to_ai(instance_id, from_number, to_number, message_type, text: str="", image: dict=None, timestamp: datetime=datetime.now()):
    ai_contexts = frappe.get_all(
        "Message Context Template",
        filters={"whatsapp_instance": instance_id},
        fields=["name", "llm", "default_model", "gpt_model", "override_model"]
    )

    if not ai_contexts:
        return None

    ai_context = ai_contexts[0]

    chat = get_chat(
        instance_id,
        from_number,
        ai_context,
    )

    model = get_model(ai_context)

    ai_response = ai_chat(
        model=model,
        chat_id=chat.name,
        message_type=message_type,
        new_message={
            "role": "user",
            "content": f"({from_number}) says: {text}",
        },
        plain_text=text,
        image=image,
        to_number=to_number,
        timestamp=timestamp,
        stream=False,
    )

    save_response_log(
        str(ai_response),
        "9999999999",
        "9999999999"
    )
    
    return ai_response


def get_chat(instance_id, from_number, ai_context):
    chats = frappe.get_all(
        "Ai Chat",
        filters={
            "context": ai_context.name,
            "whatsapp_client_id": from_number,
        },
        fields=["name", "model"]
    )

    if chats:
        chat = chats[0]
    else:
        chat = frappe.new_doc("Ai Chat")
        chat.model = get_model(ai_context)

        chat.context = ai_context.name
        chat.whatsapp_instance = instance_id
        chat.whatsapp_client_id = from_number
        chat.save(ignore_permissions=True)

        frappe.db.commit()

    return chat


def get_model(ai_context):
    if ai_context.override_model == 1:
        model = ai_context.gpt_model
    elif ai_context.default_model == 1:
        model = "gpt-oss:120b"
    else:
        model = ai_context.llm
    return model


def send_whatsapp_response(version, phone_id, token, to_number, text):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
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

    return response


def send_whatsapp_template(
    version,
    phone_id,
    token,
    to_number,
    template_name,
    language_code,
    components=None,
):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components
        }
    }
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    return response



def save_response_log(body, from_number, to_number, is_error=False):
    log = frappe.new_doc("WhatsApp Logs")
    log.from_number = from_number
    log.to_number = to_number
    log.method = "Sent"
    log.timestamp = datetime.now()
    log.body = body
    log.is_error = is_error
    log.save(ignore_permissions=True)