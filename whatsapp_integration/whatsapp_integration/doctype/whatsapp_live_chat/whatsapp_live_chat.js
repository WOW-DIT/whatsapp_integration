// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Live Chat', {
	refresh: function(frm) {
		frm.disable_save();
		build_chat_html(frm);
		get_messages(frm);
	},
	chat_id: function(frm) {
		get_messages(frm);
	}
});


function get_messages(frm) {
	if(frm.doc.chat_id) {
		frappe.call({
			method: `whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.get_messages?chat_id=${frm.doc.chat_id}`,
			callback: function(res) {
				if(res.message.success) {
					const messages = res.message.messages;
					show_messages(frm, messages);
				}
			}
		})
	}
}

function send_message(frm, messageInput) {
	if(frm.doc.chat_id) {
		frappe.call({
			method: `whatsapp_integration.whatsapp_integration.doctype.whatsapp_live_chat.whatsapp_live_chat.send_live_message`,
			args: {
				chat_id: frm.doc.chat_id,
				message_type: "text",
				text: messageInput.value(),
			},
			callback: function(res) {
				console.log(res.message);
			}
		})
	}
}


function build_chat_html(frm) {
	const chat_style = `
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
	
	console.log(messages)
	for(let msg of messages) {
		const role = msg.role;
		const type = msg.type;
		const text = msg.message_text;
		const image = msg.image;
		const timestamp = msg.timestamp;

		messages_html += `
			<div class="message_row">
				${role === "assistant" ? "<div></div>" : ""}
				<div class="${role === "assistant" ? "message_bubble" : "message_bubble_other"}">
					<div class="message_content">
						<strong>${text}</strong>
					</div>
					<div class="time_row">
						${role === "assistant" ? "<div></div>" : ""}
						<p>${timestamp}</p>
						${role === "user" ? "<div></div>" : ""}
					</div>
				</div>
				${role === "user" ? "<div></div>" : ""}
			</div>
		`;
	}

	messages_box.innerHTML = messages_html;
	messages_box.scrollTop = messages_box.scrollHeight;
}