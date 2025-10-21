// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Broadcast Message', {
	// refresh: function(frm) {

	// }
	download_excel_template(frm) {
		// window.open()
		const link = "/files/list_of_numbers.xlsx";
		window.open(link);
		// document.body.appendChild(link);
		// link.click();
		// document.body.removeChild(link);
	}
});
