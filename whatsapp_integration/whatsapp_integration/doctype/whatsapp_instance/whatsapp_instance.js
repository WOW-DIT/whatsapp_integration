// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Instance', {
	refresh: function(frm) {
		if(!frm.doc.name.startsWith("new")) {
            check_business_sub(frm);
            
            frm.add_custom_button("Clear Chats", () => {
                clearChat(frm);
            }).addClass("btn-primary");
            
            if(!frm.doc.registered) {
                frm.add_custom_button("Register Phone Number", () => {
                    register_phone_number(frm);
                }).addClass("btn-primary");
            } else {
                frm.add_custom_button("Deregister Phone Number", () => {
                    deregister_phone_number(frm);
                }).addClass("btn-primary");
            }

        }
	}
});

function clearChat(frm) {
	const d = new frappe.ui.Dialog({
        title: __(`Are you sure you want to clear chat. All chats and their messages will be removed permanently.`),
        primary_action_label: __('Clear'),
        primary_action(values) {
            d.get_primary_btn().prop('disabled', true);
            frappe.call({
                method: `whatsapp_integration.whatsapp_integration.doctype.whatsapp_instance.whatsapp_instance.clear_chats`,
				args: {
					"instance_id": frm.doc.name
				},
                freeze: true,
                freeze_message: __('Deleting all chats...'),
                callback: function(res) {
                    if(res.message.success) {
                        frappe.msgprint(res.message.message)
                        reload_page();
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            })
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}


function check_business_sub(frm) {
	frappe.call({
		method: `whatsapp_integration.whatsapp_onboarding_api.check_business_account_sub?instance_id=${frm.doc.name}`,
		callback: function(res) {
            console.log(res.message)
            if(!res.message.success) {
				frm.add_custom_button("Activate your WABA", () => {
                    sub_business_account(frm);
				});
			} else {
                frm.add_custom_button("Deactivate your WABA", () => {
                    unsub_business_account(frm);
				});
            }
		}
	})
}

function sub_business_account(frm) {
	frappe.call({
		method: `whatsapp_integration.whatsapp_onboarding_api.subscribe_business_account?instance_id=${frm.doc.name}`,
		callback: function(res) {
			if(res.message.success) {
				frappe.msgprint(res.message.message)

                frm.set_value("enabled", 1)
                frm.save()

                location.reload()
			}
		}
	})
}

function unsub_business_account(frm) {
    const d = new frappe.ui.Dialog({
        title: __(`Are you sure you want to deactivate your WABA? Enter "${frm.doc.business_account}" to confirm.`),
        fields: [
            {
                fieldname: 'confirm_code',
                label: __('Confirm Code'),
                fieldtype: 'Data',
                reqd: 1,
                description: __('Enter the WhatsApp Business Account ID to confirm.')
            }
        ],
        primary_action_label: __('Deactivate'),
        primary_action(values) {
            console.log(values)
            let confirm_code = (values.confirm_code || '').trim();

            // Allow exactly 6 letters/digits. For digits-only use: /^\d{6}$/
            if (confirm_code !== frm.doc.business_account) {
                frappe.msgprint(__('Please enter a the exact WABA ID'));
                return;
            }

            d.get_primary_btn().prop('disabled', true);
            frappe.call({
                method: `whatsapp_integration.whatsapp_onboarding_api.unsubscribe_business_account?instance_id=${frm.doc.name}`,
                freeze: true,
                freeze_message: __('Deactivating WhatsApp Business Account...'),
                callback: function(res) {
                    if(res.message.success) {
                        frappe.msgprint(res.message.message)
                        reload_page();
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            })
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}

function register_phone_number(frm) {
	const d = new frappe.ui.Dialog({
        title: __('Enter Registration PIN'),
        fields: [
            {
                fieldname: 'pin',
                label: __('PIN'),
                fieldtype: 'Password',
                reqd: 1,
                description: __('Enter the 6-character PIN')
            }
        ],
        primary_action_label: __('Register'),
        primary_action(values) {
            let pin = (values.pin || '').trim();

            // Allow exactly 6 letters/digits. For digits-only use: /^\d{6}$/
            if (!/^[A-Za-z0-9]{6}$/.test(pin)) {
                frappe.msgprint(__('Please enter a valid 6-character PIN (letters/digits).'));
                return;
            }

            d.get_primary_btn().prop('disabled', true);

            frappe.call({
                method: 'whatsapp_integration.whatsapp_onboarding_api.register_phone_number',
                args: {
                    instance_id: frm.doc.name,
                    pin: pin
                },
                freeze: true,
                freeze_message: __('Registering phone number...'),
                callback(res) {
					console.log(res.message)
                    d.hide();
                    if (res.message && res.message.success) {
                        frappe.msgprint(res.message.message || __('Phone number registered successfully.'));
                        reload_page();
                    } else {
                        frappe.msgprint(res.message?.message || __('Registration failed.'));
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}

function deregister_phone_number(frm) {
	const d = new frappe.ui.Dialog({
        title: __(`Are you sure you want to deregister your phone number?\n Enter "${frm.doc.name}" to confirm.`),
        fields: [
            {
                fieldname: 'confirm_code',
                label: __('Confirm Code'),
                fieldtype: 'Data',
                reqd: 1,
                description: __('Enter the Instance ID to confirm.')
            }
        ],
        primary_action_label: __('Deregister'),
        primary_action(values) {
            console.log(values)
            let confirm_code = (values.confirm_code || '').trim();

            // Allow exactly 6 letters/digits. For digits-only use: /^\d{6}$/
            if (confirm_code !== frm.doc.name) {
                frappe.msgprint(__('Please enter a the exact instance id'));
                return;
            }

            d.get_primary_btn().prop('disabled', true);

            frappe.call({
                method: 'whatsapp_integration.whatsapp_onboarding_api.deregister_phone_number',
                args: {
                    instance_id: frm.doc.name,
                },
                freeze: true,
                freeze_message: __('Deregistering phone number...'),
                callback(res) {
					console.log(res.message)
                    d.hide();
                    if (res.message && res.message.success) {
                        frappe.msgprint(res.message.message || __('Phone number deregistered successfully.'));
                        reload_page();
                    } else {
                        frappe.msgprint(res.message?.message || __('Deregistration failed.'));
                    }
                },
                always() {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    // Submit on Enter
    d.$wrapper.find('input').on('keydown', (e) => {
        if (e.key === 'Enter') d.get_primary_btn().click();
    });

    d.show();
}

function reload_page(){
    setTimeout(() => {
        location.reload();
    }, 3000);
}