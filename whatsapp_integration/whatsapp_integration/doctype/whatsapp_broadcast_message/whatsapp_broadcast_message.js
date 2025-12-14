// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Broadcast Message', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new") && frm.doc.status === "Pending") {
			frm.add_custom_button(__('Send'), function() {
                // This function runs when the button is clicked
                frappe.call({
                    method: "whatsapp_integration.whatsapp_integration.doctype.whatsapp_broadcast_message.whatsapp_broadcast_message.submit_broadcast",
                    args: {
                        reference_id: frm.doc.name,
                    },
					freeze: true, 
    				freeze_message: __("Sending..."),
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint(r.message);
                            // // Refresh the form after the action is complete
                            // frm.refresh_field('status'); // Example: refresh a specific field
                            // frm.reload_doc();           // Example: reload the entire document
                        }
                    }
                });
            }).addClass("btn-primary");
		}
	},
	download_excel_template(frm) {
		// window.open()
		const link = "/files/list_of_numbers.xlsx";
		window.open(link);
		// document.body.appendChild(link);
		// link.click();
		// document.body.removeChild(link);
	}
});
