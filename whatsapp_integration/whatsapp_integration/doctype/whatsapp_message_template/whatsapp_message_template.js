// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Message Template', {
	// refresh: function(frm) {

	// }
	header_example_file: function(frm) {
		frm.set_value("document_handle_id", "")
		frm.save()
	}
});
