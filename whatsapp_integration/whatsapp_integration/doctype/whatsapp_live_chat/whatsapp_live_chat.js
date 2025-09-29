// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Live Chat', {
	refresh: function(frm) {
		frm.disable_save();
		build_chat_html(frm);
		set_chat(frm);
		get_messages(frm);
	},
	chat_id: function(frm) {
		get_messages(frm);
	}
});

// keep track of the current room subscription
function switch_room(frm) {
    if (!frm.doc.chat_id) return;

    // unsubscribe old
    if (frm._current_room && frappe.realtime?.unsubscribe) {
        try { frappe.realtime.unsubscribe(frm._current_room); } catch (e) {}
    }
    // subscribe new
    frm._current_room = frm.doc.chat_id;
    if (frappe.realtime?.subscribe) {
        frappe.realtime.subscribe(frm._current_room);
    }
}

function bind_realtime(frm) {
    if (frm._realtime_bound) return; // bind once
    frm._realtime_bound = true;

    frappe.realtime.on(`whatsapp_chat_${frm.doc.chat_id}`, (data) => {

        if (!data || !frm.doc.chat_id) return;
        append_message(frm, data);
    });
}

function append_message(frm, msg) {
	const messages_box = document.getElementById("messages");
	const role = msg.role;
	// const type = msg.type;
	const text = msg.message;
	// const image = msg.image;
	const timestamp = msg.timestamp;//.split(".")[0];
	const is_assistant = role !== "user";

	let new_message = `
		<div class="message_row">
			${is_assistant ? "<div></div>" : ""}
			<div class="${role !== "user" ? "message_bubble" : "message_bubble_other"}">
				<div class="message_content">
					<strong>${text}</strong>
				</div>
				<div class="time_row">
					${is_assistant ? "<div></div>" : ""}
					<p>${timestamp}</p>
					${!is_assistant ? "<div></div>" : ""}
				</div>
			</div>
			${!is_assistant ? "<div></div>" : ""}
		</div>
	`;
	messages_box.innerHTML += new_message;
	messages_box.scrollTop = messages_box.scrollHeight;
}


function set_chat(frm) {
	const params = new URLSearchParams(window.location.search);
	const chat_id = params.get("chat_id");

	if(chat_id) {
		frm.set_value("chat_id", chat_id)
	}
}


function get_messages(frm) {
	const messages_box = document.getElementById("messages");
	if (!frm.doc.chat_id) {
		if (messages_box) messages_box.innerHTML = "";
		return;
	}

	if (messages_box) messages_box.innerHTML = "";
	setInputEnabled(false);
	showPanelLoader();

	frappe.call({
		method: `whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.get_messages?chat_id=${frm.doc.chat_id}`,
		freeze: true,
		freeze_message: __("Fetching messages…"),
		callback: function(res) {
			hidePanelLoader();
			setInputEnabled(true);

			if (res?.message?.success) {
				const messages = res.message.messages || [];
				show_messages(frm, messages);
			} else {
				frappe.msgprint({ title: __("Error"), message: __("Failed to load messages."), indicator: "red" });
			}
		},
		error: function() {
			hidePanelLoader();
			setInputEnabled(true);
			frappe.msgprint({ title: __("Error"), message: __("Failed to load messages."), indicator: "red" });
		}
	})
}

function send_message(frm, messageInput) {
	const new_message_text = messageInput.value;
	const data = {
		message: new_message_text,
		role: "assistant",
		timestamp: new Date()
	}
	append_message(frm, data);
	messageInput.value = "";

	if(frm.doc.chat_id) {
		frappe.call({
			method: `whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.send_live_message`,
			args: {
				chat_id: frm.doc.chat_id,
				message_type: "text",
				text: new_message_text,
			},
			callback: function(res) {
				console.log(res.message);
				if(res.message.success) {
					
				}
			}
		})
	}
}


function build_chat_html(frm) {
	const chat_style = `
		#chat_container { position: relative; }
		#chat_loader { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 5; }
		.loader_backdrop { position: absolute; inset: 0; background: rgba(255,255,255,0.65); backdrop-filter: blur(1px); }
		.loader_box { position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px 16px; border-radius: 8px; background: #ffffff; border: 1px solid #e5e7eb; box-shadow: 0 8px 24px rgba(0,0,0,0.08);}
		.loader_text { font-size: 12px; color: #6b7280; }

		/* Dual ring spinner (no external deps) */
		.lds-dual-ring {
			display: inline-block;
			width: 28px;
			height: 28px;
		}
		.lds-dual-ring:after {
			content: " ";
			display: block;
			width: 28px;
			height: 28px;
			margin: 1px;
			border-radius: 50%;
			border: 3px solid #0FCE01;
			border-color: #0FCE01 transparent #0FCE01 transparent;
			animation: lds-dual-ring 1.2s linear infinite;
		}
		@keyframes lds-dual-ring {
			0% { transform: rotate(0deg); }
			100% { transform: rotate(360deg); }
		}
		#chat_container {
			width: 100%;
			height: 450px;
			background-color: #f8f8f8;
			display: flex;
			flex-direction: column;
			justify-content: space-between;
			padding: 10px;
			border: 1px solid #ddd;
			border-radius: 8px;
		}

		#messages {
			flex: 1;
			max-height: 350px;
			overflow-y: auto;
			padding: 5px;
			border: 1px solid #ccc;
			background: white;
			border-radius: 4px;
			margin-bottom: 8px;
			display: flex;
			flex-direction: column;
			gap: 25px;
		}

		#input-row {
			display: flex;
			gap: 8px;
		}

		#message-input {
			flex: 1;
			padding: 6px;
			border: 1px solid #ccc;
			border-radius: 4px;
		}

		#send-btn {
			background: #007bff;
			color: white;
			border: none;
			padding: 6px 12px;
			border-radius: 4px;
			cursor: pointer;
		}

		#send-btn:hover {
			background: #0056b3;
		}
		
		.message_row {
			display: flex;
			justify-content: space-between;
			align-items: center;
		}

		.message_bubble {
			padding: 10px;
			background-color: #0FCE01;
			color: white;
			border-radius: 5px;
			display: flex;
			flex-direction: column;
			gap: 10px;
			max-width: 60%;
		}

		.message_bubble_other {
			padding: 10px;
			background-color: #B6B6B6;
			color: black;
			border-radius: 5px;
			display: flex;
			flex-direction: column;
			gap: 10px;
			max-width: 60%;
		}
		
		.time_row {
			display: flex;
			justify-content: space-between;
			align-items: center;
		}

		.time_row p {
			padding: 0px;
			margin: 0px;
			color: #717171;
		}
	`;

	frm.fields_dict["chat_html"].$wrapper.html(`
		<div id="chat_container">
			<div id="messages">
				
			</div>
			<div id="input-row">
				<input id="message-input" name="message-input" placeholder="Write a message"/>
				<button type="button" id="send-btn">>></button>
			</div>
		</div>
		<style>
			${chat_style}
		</style>
	`);

	const messageInput = document.getElementById("message-input");
	const sendBtn = document.getElementById("send-btn");
	sendBtn.addEventListener("click", (e) => {
		send_message(frm, messageInput);
	})

}

function show_messages(frm, messages) {
	const messages_box = document.getElementById("messages");
	let messages_html = "";
	
	for(let msg of messages) {
		const role = msg.role;
		const type = msg.type;
		const text = msg.message_text;
		const image = msg.image;
		const timestamp = msg.timestamp;// === null ? "" : msg.timestamp.split(".")[0];
		const is_assistant = role !== "user";

		messages_html += `
			<div class="message_row">
				${is_assistant ? "<div></div>" : ""}
				<div class="${is_assistant ? "message_bubble" : "message_bubble_other"}">
					<div class="message_content">
						<strong>${text}</strong>
					</div>
					<div class="time_row">
						${is_assistant ? "<div></div>" : ""}
						<p>${timestamp}</p>
						${!is_assistant ? "<div></div>" : ""}
					</div>
				</div>
				${!is_assistant ? "<div></div>" : ""}
			</div>
		`;
	}

	messages_box.innerHTML = messages_html;
	messages_box.scrollTop = messages_box.scrollHeight;


	bind_realtime(frm);
	frm.add_custom_button("End Live", () => {
		endLiveSession(frm);
	}).addClass("btn-primary");
}

function endLiveSession(frm) {
	frappe.call({
		method: "whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.end_live_session",
		args: {
			chat_id: frm.doc.chat_id
		},
		callback: function(r) {
			if(r.message.success) {
				frm.set_value("chat_id", "");
				location.href = r.message.url;
			}
		}
	})
}

// --- Loading helpers ---
function setInputEnabled(enabled) {
	const input = document.getElementById("message-input");
	const btn = document.getElementById("send-btn");
	if (input) input.disabled = !enabled;
	if (btn) btn.disabled = !enabled;
}

function showPanelLoader() {
	const c = document.getElementById("chat_container");
	if (!c) return;
	if (!document.getElementById("chat_loader")) {
		const loader = document.createElement("div");
		loader.id = "chat_loader";
		loader.innerHTML = `
			<div class="loader_backdrop"></div>
			<div class="loader_box">
				<div class="lds-dual-ring"></div>
				<div class="loader_text">Loading…</div>
			</div>
		`;
		c.appendChild(loader);
	}
}

function hidePanelLoader() {
	const el = document.getElementById("chat_loader");
	if (el) el.remove();
}
