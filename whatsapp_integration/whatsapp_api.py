import frappe
from werkzeug.wrappers import Response
from datetime import datetime
from ai_intergration.ai_intergration.api import ai_chat, speech_to_text, text_to_speech
from ai_intergration.ai_intergration.api_v2 import ai_chat_v2, speech_to_text, text_to_speech
import requests
import json
from io import BytesIO
import uuid
import os
import hashlib
import hmac

@frappe.whitelist()
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
    latitude=None,
    longitude=None,
    address=None,
    location_name=None,
    image_url=None,
    image_caption=None,

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
            direct_call=False,
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
            direct_call=False,
        )

    elif type == "location":
        response = send_whatsapp_location(
            version=api_version,
            phone_id=phone_id,
            token=token,
            to_number=client_number,
            latitude=latitude,
            longitude=longitude,
            name=location_name,
            address=address,
            direct_call=False,
        )

    elif type == "image":
        response = send_whatsapp_image(
            version=api_version,
            phone_id=phone_id,
            token=token,
            to_number=client_number,
            url=image_url,
            image_caption=image_caption,
            direct_call=False,
        )
            

    return response


@frappe.whitelist()
def get_whatsapp_message(msg_id, api_version, ):
    response = requests.get(f"https://graph.facebook.com/{api_version}")


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
        wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
        try:
            raw_body = frappe.request.data

            # Get the signature from headers
            received_sig = frappe.get_request_header("X-Hub-Signature-256")

            # Compute expected signature
            app_secret = wa_settings.get_password("app_secret")
            expected_sig = "sha256=" + hmac.new(
                key=app_secret.encode("utf-8"),
                msg=raw_body,
                digestmod=hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(received_sig, expected_sig):
                frappe.log_error("Invalid WhatsApp webhook signature")
                frappe.throw("Invalid signature", frappe.PermissionError)


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
                        template_id = value.get("message_template_id")
                        status = value.get("event")

                        update_template(str(template_id), str(status))
                    except:
                        continue
                    finally:
                        continue
                

                phone_id = value["metadata"]["phone_number_id"]
                messages = value.get("messages")
                statuses = value.get("statuses")
                
                if statuses:
                    ## Search for whatsapp instance by business id
                    wa_instances = frappe.get_all(
                        "WhatsApp Instance",
                        filters={"business_id": business_id, "enabled": 1},
                        limit=1,
                    )
                    if not wa_instances:
                        raise Exception("Business user is not subscribed")

                    wa_instance = frappe.get_doc("WhatsApp Instance", wa_instances[0].name)
                    user = wa_instance.user
                    token = wa_instance.get_password("token")

                    context = get_ai_context(wa_instance.name)
                    if not context:
                        raise Exception("service is currently down. we will be back soon.")

                    for st in statuses:
                        msg_id = st.get("id")
                        msg_status = st.get("status")
                        recipient_id = st.get("recipient_id")
                        conversation = st.get("conversation")

                        chat = get_chat(wa_instance.name, recipient_id, context)
                        # if not conversation:
                        #     ## Turn on live chat mode
                        #     frappe.db.set_value(
                        #         "Ai Chat",
                        #         chat.name,
                        #         "is_live",
                        #         1,
                        #         update_modified=False,
                        #     )



                if messages:
                    api_version = wa_settings.api_version

                    wa_instances = frappe.get_all(
                        "WhatsApp Instance",
                        filters={"business_id": business_id, "enabled": 1},
                        limit=1,
                    )
                    if not wa_instances:
                        raise Exception("Business user is not subscribed")

                    wa_instance = frappe.get_doc("WhatsApp Instance", wa_instances[0].name)
                    user = wa_instance.user
                    token = wa_instance.get_password("token")

                    context = get_ai_context(wa_instance.name)
                    if not context:
                        raise Exception("service is currently down. we will be back soon.")
                    
                    from_number = messages[0]["from"]
                    to_number = value["contacts"][0]["wa_id"]
                    try:
                        client_subscription = get_sub(wa_instance.customer_id)
                        if client_subscription is None:
                            error_message = str(wa_instance.error_message).strip() if wa_instance.error_message else ""
                            if error_message:
                                raise Exception(error_message)
                            else:
                                return
                            
                        sub_id = client_subscription.name
                        enough_balance = has_enough_balance(sub_id)

                        if not enough_balance:
                            return

                        converted_audio_to_text = False
                        converted_text_to_audio = False

                        for msg in messages:
                            timestamp = datetime.fromtimestamp(float(msg["timestamp"]))
                            message_type = msg["type"]
                            image = None

                            if message_type == "text":
                                msg_body = msg["text"]["body"]
                            
                            elif message_type == "audio":
                                stt_error = wa_instance.stt_error_message if wa_instance.stt_error_message else wa_settings.stt_error_message
                                stt_model = wa_settings.stt_model
                                
                                try:
                                    if wa_settings.allow_stt == 0 or wa_instance.allow_stt == 0:
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

                                    if msg_body:
                                        converted_audio_to_text = True
                                        
                                except Exception as e:
                                    wa_message = send_whatsapp_response(
                                        version=api_version,
                                        phone_id=phone_id,
                                        token=token,
                                        to_number=to_number,
                                        text=stt_error,
                                        direct_call=False,
                                    )
                                    return

                            elif message_type == "image":
                                try:
                                    if context.override_model == 0:
                                        raise Exception("Sending images is currently not supported")
                                    
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
                                        direct_call=False,
                                    )
                                    return
                            elif message_type == "interactive":
                                interactive_template = get_interactive_template(instance_id=wa_instance.name)
                                if interactive_template and interactive_template.integration == 1:
                                    interactive_body = {
                                        "whatsapp_instance_id": wa_instance.name,
                                        "user_number": to_number,
                                        "interactive": msg.get("interactive")
                                    }
                                    send_interactive_webhook(interactive_template, interactive_body)
                                    # save_response_log(str(rrr), "babababa", "babababa")
                                
                                return

                            from_number = msg["from"]

                            try:
                                chat = get_chat(
                                    wa_instance.name,
                                    from_number,
                                    context,
                                )

                                model = get_model(context)

                                if wa_instance.v2:
                                    ai_response = ai_chat_v2(
                                        model=model,
                                        chat_id=chat.name,
                                        message_type=message_type,
                                        new_message={
                                            "role": "user",
                                            "content": f"({from_number}) says: {msg_body}",
                                        },
                                        plain_text=msg_body,
                                        image=image,
                                        to_account=to_number,
                                        timestamp=timestamp,
                                        stream=False,
                                        context=context,
                                    )
                                else:
                                    ai_response = ai_chat(
                                        model=model,
                                        chat_id=chat.name,
                                        message_type=message_type,
                                        new_message={
                                            "role": "user",
                                            "content": f"({from_number}) says: {msg_body}",
                                        },
                                        plain_text=msg_body,
                                        image=image,
                                        to_account=to_number,
                                        timestamp=timestamp,
                                        stream=False,
                                        context=context,
                                    )

                                if not ai_response:
                                    error_msg = context.on_error if context.on_error else "عذرا لم أفهم، ممكن تكرر الطلب من فضلك."
                                    raise Exception(error_msg)


                                is_live = ai_response.get("is_live")
                                response_text = ai_response.get("response")
                                response_type = ai_response.get("message_type")
                                file_link = ai_response.get("file_link")
                                caption = ai_response.get("caption", "")

                                if is_live:
                                    frappe.publish_realtime(
                                        f"whatsapp_chat_{chat.name}",
                                        message={
                                            "message": msg_body,
                                            "sender": from_number,
                                            "role": "user",
                                            "timestamp": timestamp,
                                        }
                                    )

                                elif response_text:
                                    ## Sending audio response to the user
                                    if message_type == "audio":
                                        tts_model = wa_settings.tts_model
                                        tts_voice = wa_instance.voice_type if wa_instance.voice_type else "alloy"

                                        try:
                                            audio_file_link = text_to_speech(
                                                tts_model,
                                                context.client_credentials,
                                                response_text,
                                                tts_voice,
                                            )
                                            wa_message = send_whatsapp_audio_link(
                                                version=api_version,
                                                phone_id=phone_id,
                                                token=token,
                                                to_number=to_number,
                                                file_link=audio_file_link,
                                                direct_call=False,
                                            )

                                        ## Return to default response content type (text)
                                        except:
                                            wa_message = send_whatsapp_response(
                                                version=api_version,
                                                phone_id=phone_id,
                                                token=token,
                                                to_number=to_number,
                                                text=response_text,
                                                direct_call=False,
                                            )

                                    ## Default (Send text)
                                    else:
                                        wa_message = send_whatsapp_response(
                                            version=api_version,
                                            phone_id=phone_id,
                                            token=token,
                                            to_number=to_number,
                                            text=response_text,
                                            direct_call=False,
                                        )

                                    if wa_message.status_code == 200:
                                        number_of_points = calculate_deducted_balance(
                                            wa_settings,
                                            converted_audio_to_text,
                                            converted_text_to_audio,
                                        )
                                        
                                        spent = spend_balance(sub_id, number_of_points)

                                    if response_type == "text" or wa_instance.v2:
                                        return
                                    
                                    if response_type == "document":
                                        wa_message = send_whatsapp_document_link(
                                            version=api_version,
                                            phone_id=phone_id,
                                            token=token,
                                            to_number=to_number,
                                            file_link=file_link,
                                            caption=caption,
                                            direct_call=False,
                                        )

                                    if response_type == "image":
                                        wa_message = send_whatsapp_image_link(
                                            version=api_version,
                                            phone_id=phone_id,
                                            token=token,
                                            to_number=to_number,
                                            file_link=file_link,
                                            image_caption=caption,
                                            direct_call=False,
                                        )

                                    if wa_message.status_code == 200:
                                        spent = spend_balance(sub_id)

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
                                    direct_call=False,
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
                            direct_call=False,
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


def get_interactive_template(instance_id):
    interactive_temp_id = frappe.get_value(
        "WhatsApp Interactive Template",
        {"whatsapp_instance": instance_id},
    )

    if interactive_temp_id:
        interactive_temp = frappe.get_doc("WhatsApp Interactive Template", interactive_temp_id)
        return interactive_temp
    else:
        return None
    

def send_interactive_webhook(interactive_template, body: dict):
    try:
        url = interactive_template.webhook_url
        api_key = interactive_template.get_password("api_key")
        auth_type = interactive_template.auth_type

        headers = {}
        # if api_key:
        #     headers["Authorization"] = f"{auth_type} {api_key}"

        response = requests.post(url, headers=headers, json=body)

        return response.text
    
    except Exception as e:
        return str(e)

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
        file_name = file_url.split("/")[-1]
        url = f"https://graph.facebook.com/{api_version}/{phone_id}/media"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        files = {
            "file": (file_name, open(f"/home/frappe/frappe-bench/sites/whatsapp.wowdigital.sa/public/files/{file_name}", "rb"), mime_type),
            "messaging_product": (None, "whatsapp")
        }

        response = requests.post(url, headers=headers, files=files)
        
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


def has_enough_balance(sub_id):
    balance = frappe.db.get_value(
        "Connectly Subscription",
        sub_id,
        "balance"
    )
    if balance <= 0:
        return False
    return True


def spend_balance(sub_id, number_of_points=1):
    try:
        last_balance = frappe.db.get_value(
            "Connectly Subscription",
            sub_id,
            "balance"
        )

        frappe.db.set_value(
            "Connectly Subscription",
            sub_id,
            "balance",
            (last_balance - number_of_points),
            update_modified=False,
        )
        return True
    except:
        return False
    

def calculate_deducted_balance(wa_settings, converted_audio_to_text, converted_text_to_audio):
    number_of_points = 1

    if converted_audio_to_text and wa_settings.charge_on_stt:
        number_of_points += wa_settings.stt_balance_points

    if converted_text_to_audio and wa_settings.charge_on_tts:
        number_of_points += wa_settings.tts_balance_points

    return number_of_points


def get_sub(customer_id):
    try:
        subs = frappe.get_all(
            "Connectly Subscription",
            filters={"name": customer_id, "enabled": 1},
            limit=1,
        )
        if subs:
            sub = frappe.get_doc("Connectly Subscription", subs[0].name)
            return sub
        
        return None
    except:
        return None


def get_ai_context(instance_id):
    ai_contexts = frappe.get_all(
        "AI Agent",
        filters={"whatsapp_instance": instance_id},
        fields=["*"],
        limit=1,
    )

    if not ai_contexts:
        return None

    ai_context = ai_contexts[0]
    return ai_context


def get_chat(instance_id, from_user, ai_context):
    chats = frappe.get_all(
        "Ai Chat",
        filters={
            "whatsapp_instance": instance_id,
            "user_id": from_user,
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
        chat.user_id = from_user
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


def send_whatsapp_response(
    version,
    phone_id,
    token,
    to_number,
    text,
    direct_call=True,
):
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

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_location(
    version,
    phone_id,
    token,
    to_number,
    latitude,
    longitude,
    name,
    address,
    direct_call=True,
):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "location",
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "name": name,
            "address": address
        }
    }


    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_template(
    version,
    phone_id,
    token,
    to_number,
    template_name,
    language_code,
    components=None,
    direct_call=True,
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

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_interactive(
    version,
    phone_id,
    token,
    to_number,
    header_text,
    body_text,
    footer_text,
    button_text,
    sections,
    direct_call=True,
):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": body_text
            },
            "footer": {
                "text": footer_text,
            },
            "action": {
                "button": button_text,
                "sections": sections,
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()

    return response


@frappe.whitelist(methods=["POST"])
def send_whatsapp_interactive_standalone(
    instance_id,
    to_number,
    header_text,
    body_text,
    footer_text,
    button_text,
    sections,
    direct_call=True,
):
    wa_settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
    version = wa_settings.api_version

    wa_instance = frappe.get_doc("WhatsApp Instance", instance_id)
    phone_id = wa_instance.phone_id
    token = wa_instance.get_password("token")

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": header_text
            },
            "body": {
                "text": body_text
            },
            "footer": {
                "text": footer_text,
            },
            "action": {
                "button": button_text,
                "sections": sections,
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()

    return response


def send_whatsapp_image(version, phone_id, token, to_number, url, image_caption, direct_call=True):
    mime_type = get_mime_type(url.split(".")[-1])
    media = upload_media(
        mime_type=mime_type,
        api_version=version,
        phone_id=phone_id,
        token=token,
        file_url=url,
    )

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "image",
        "image": {
            "id" : media["id"],
            "caption": image_caption
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_image_link(version, phone_id, token, to_number, file_link, caption, direct_call=True):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "image",
        "image": {
            "link" : file_link,
            "caption": caption,
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()

    return response


def send_whatsapp_document(version, phone_id, token, to_number, url, caption, direct_call=True):
    mime_type = get_mime_type(url.split(".")[-1])
    media = upload_media(
        mime_type=mime_type,
        api_version=version,
        phone_id=phone_id,
        token=token,
        file_url=url,
    )
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "document",
        "document": {
            "id" : media["id"],
            "caption": caption,
            "filename": "file.pdf"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)
    
    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


@frappe.whitelist(allow_guest=True)
def send_whatsapp_document_link(version, phone_id, token, to_number, file_link, caption="", direct_call=True):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "document",
        "document": {
            "link" : file_link,
            "caption": caption,
            "filename": "file.pdf"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_audio(version, phone_id, token, to_number, url, direct_call=True):
    mime_type = get_mime_type(url.split(".")[-1])
    media = upload_media(
        mime_type=mime_type,
        api_version=version,
        phone_id=phone_id,
        token=token,
        file_url=url,
    )

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "audio",
        "audio": {
            "id": media["id"],
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
    return response


def send_whatsapp_audio_link(version, phone_id, token, to_number, file_link, direct_call=True):
    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "audio",
        "audio": {
            "link": file_link,
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=body, headers=headers)

    if direct_call:
        frappe.response["success"] = response.status_code == 200
        return response.json()
    
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