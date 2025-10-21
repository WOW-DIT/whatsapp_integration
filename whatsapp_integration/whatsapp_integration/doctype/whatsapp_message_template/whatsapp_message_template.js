// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt
const style = `
	#preview_background {
		display: flex;
		width: 100%;
		background-color: green;
		padding: 20px;
	}
	#message {
		padding: 4px;
		background-color: white;
		width: 70%;
		border-radius: 6px;
		gap: 10px;
		max-width: 300px;
	}
	#header_file {
		height: 150px;
		background-color: #DCDCDC;
		border-radius: 6px;
		display: flex;
		justify-content: center;
		align-items: center;
	}
	.file_icon {
		width: 50px;
	}
	#preview_body {
		white-space: pre-line;
	}
	#preview_footer p{
		margin: 0px;
		margin-top: 5px;
		color: #949494ff;
	}
	#footer_text {
		font-size: 9pt;
	}
	#footer_time {
		font-size: 8pt;
	}
`;
frappe.ui.form.on('WhatsApp Message Template', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
			build_preview(frm);
		}
	},
	body: function(frm) {
		update_preview_body(frm);
	},
	body_examples: function(frm) {
		update_preview_body(frm);
	},
	header_format: function(frm) {
		update_preview_header(frm);
	},
	header_text: function(frm) {
		update_preview_header(frm);
	},
	header_examples: function(frm) {
		update_preview_header(frm);
	},
	header_example_file: function(frm) {
		frm.set_value("document_handle_id", "");
		frm.save();
	}
});


function update_preview_header(frm) {
	const preview_header = document.getElementById("preview_header");
	console.log(preview_header);
	preview_header.innerHTML = `
		${
			frm.doc.header_format === "TEXT"?
				`<h3
				${
					frm.doc.language === "ar" ? 
					`style="text-align: right; direction: rtl; unicode-bidi: plaintext;"` :
					``
				}>
					${get_header_text(frm)}
				</h3>` :
				`<div id="header_file">
					<div id="image_frame">
						${frm.doc.header_format === "DOCUMENT"?
							`<i class="fa fa-file-pdf-o fa-4x" aria-hidden="true"></i>` :
							`<i class="fa fa-picture-o fa-4x" aria-hidden="true"></i>`
						}
					</div>
				</div>`
		}
	`;
}

function update_preview_body(frm) {
	const preview_body = document.getElementById("preview_body");
	preview_body.textContent = frm.doc.body || "";
}

function build_preview(frm){
	const now_hour = frappe.datetime.now_time().split(":")[0];
	const now_minute = frappe.datetime.now_time().split(":")[1];
	
	let preview_html = `
	<style>
		${style}
	</style>
	<div id="preview_background">
		<div id="message" class="d-flex flex-column">
			<div id="preview_header">
				${
					frm.doc.header_format === "TEXT"?
						`<h3
						${
							frm.doc.language === "ar" ? 
							`style="text-align: right; direction: rtl; unicode-bidi: plaintext;"` :
							``
						}>
							${get_header_text(frm)}
						</h3>` :
						`<div id="header_file">
							<div id="image_frame">
								${frm.doc.header_format === "DOCUMENT"?
									`<i class="fa fa-file-pdf-o fa-4x" aria-hidden="true"></i>` :
									`<i class="fa fa-picture-o fa-4x" aria-hidden="true"></i>`
								}
							</div>
						</div>`
				}
			</div>
			<div 
				id="preview_body" 
				${
					frm.doc.language === "ar" ? 
					`style="text-align: right; direction: rtl; unicode-bidi: plaintext;"` :
					``
				}>
				${frm.doc.body || ""}
			</div>
			<div id="preview_footer" class="d-flex justify-content-between">
				<p id="footer_text">${frm.doc.footer || ""}</p>
				<p id="footer_time">${now_hour}:${now_minute}</p>
			</div>
		</div>
	</div>
	`;

	frm.fields_dict.message_preview.wrapper.innerHTML = preview_html;
}

function get_header_text(frm) {
	const text = frm.doc.header_text;
	const examples = frm.doc.header_examples ? frm.doc.header_examples.split("|") : [];

	if(examples.length > 0) {
		for(let i = 0; i <= examples.length; i++) {
			const example = examples[i];
			text.replace(`{{${i+1}}}`, example);
		}
	}
	console.log(text);
	return text || "";
}

function get_body_text(frm) {
	const text = frm.doc.body;
	const examples = frm.doc.body_examples ? frm.doc.body_examples.split("|") : [];
	if(examples.length > 0) {
		for(let i = 0; i <= examples.length; i++) {
			const example = examples[i];
			text.replace(`{{${i+1}}}`, example);
		}
	}

	console.log(text);
	return text || "";
}