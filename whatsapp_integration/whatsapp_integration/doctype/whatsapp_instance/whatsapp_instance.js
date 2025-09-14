// Copyright (c) 2025, Mosaab Bleik and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Instance', {
	refresh: function(frm) {
		check_business_sub(frm);

		if(!frm.doc.registered) {
			frm.add_custom_button("Register Phone Number", () => {
				register_phone_number(frm);
			}).addClass("btn-primary");
		}
	}
});


function check_business_sub(frm) {
	frappe.call({
		method: `whatsapp_integration.whatsapp_onboarding_api.check_business_account_sub?instance_id=${frm.doc.name}`,
		callback: function(res) {
            if(!res.message.success) {
                console.log(res.message)
				frm.add_custom_button("Activate your WABA", () => {
                    sub_business_account(frm)
				});
			}
		}
	})
}

function sub_business_account(frm) {
	frappe.call({
		method: `whatsapp_integration.whatsapp_onboarding_api.subscribe_business_account?instance_id=${frm.doc.name}`,
		callback: function(res) {
            console.log(res.message)
			if(res.message.success) {
				frappe.msgprint(res.message.message)

                frm.set_value("enabled", 1)
                frm.save()
			}
		}
	})
}

function register_phone_number(frm) {
	const d = new frappe.ui.Dialog({
        title: __('Enter Registration PIN'),
        fields: [
            {
                fieldname: 'pin',
                label: __('PIN'),
                fieldtype: 'Password', // masked input; change to 'Data' if you prefer visible
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
                        frappe.msgprint(res.message.message || __('Registered successfully.'));
						
						frm.set_value("registered", 1);
						frm.save();
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