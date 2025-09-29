// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Subscription', {
	refresh: function(frm) {

	}
});


function toggle_activity(frm, active) {
	frappe.call({
		method: "whatsapp_integration.whatsapp_integration.doctype.whatsapp_subscription.toggle_activity",
		args: {
			active: active
		}
	})
}
