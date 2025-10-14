# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

import frappe
from .fraud_prevention import get_fraud_prevention_headers

accept_header = { "Accept": "application/vnd.hmrc.1.0+json" }

@frappe.whitelist()
def fraud_prevention_header_feedback(company):
    oauth = get_session(company)
    api_hostname = frappe.get_doc("HMRC API Settings").api_hostname
    response = oauth.get(
        api_hostname+"/test/fraud-prevention-headers/vat-mtd/validation-feedback",
        headers=accept_header)
    return response.json()

def get_session(company: str):
    # TODO: Sessions should be per company, not per user.
    # (Frappe Connected App limitation)
    app_name = frappe.get_single_value("HMRC API Settings", "connected_app")
    if not app_name:
        frappe.throw("No Connected App configured in HMRC API Settings")
    app = frappe.get_doc("Connected App", app_name)
    return app.get_oauth2_session(frappe.session.user)

@frappe.whitelist()
def mark_success(name: str):
    """Mark the HMRC Authorisation as successful, after OAuth callback.
    (Putting it in HMRC Authorisations doctype sometimes fails because of a
    140 character limit on Success URI.)
    """
    hmrc_auth = frappe.get_doc("HMRC Authorisations", name)
    if hmrc_auth:
        hmrc_auth.set("authorisation_status", "Authorised")
        hmrc_auth.save()
        frappe.db.commit()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = hmrc_auth.get_url()
        frappe.msgprint("Authorization successful. You can close this window.")
    else:
        frappe.throw("HMRC Authorisation not found")