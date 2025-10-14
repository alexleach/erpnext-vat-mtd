// Copyright (c) 2020 Software to Hardware Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('HMRC API Settings', {
	refresh: function(frm) {

		frm.add_custom_button(__('Test HMRC Connectivity'), function() {
			frm.call({
				method : "test_api",
				doc: frm.doc,
				callback : function(r){
					frappe.msgprint("HMRC connectivity test success!");
				}
			});
		});

	},

	create_app: function(frm) {
		frm.call({
			method : "create_app",
			doc: frm.doc,
			callback : function(r){
				frappe.msgprint("Connected App created/updated. Please update its Client ID and Secret.");
				frm.reload_doc();
			}
		});
	}

});
