# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_link_to_form
from .fraud_prevention import get_fraud_prevention_headers

accept_header = { "Accept": "application/vnd.hmrc.1.0+json" }

def is_company_vat_enabled(company):
    enabled_count = frappe.db.sql("""
                select count(name) `tabHMRC Authorisations` a
                where
                    a.company = %s and
                    a.authorisation_status = "Authorised"
                """, company)[0][0]

    return enabled_count > 0

def get_vrn(company: str) -> str:
    tax_id = frappe.db.get_value("Company", company, "tax_id")
    if not tax_id:
        link = get_link_to_form("Company", company)
        frappe.throw(f"Please set the Tax ID for company {link}.")
    if not tax_id.upper().startswith("GB"):
        frappe.throw("Company Tax ID is invalid. Should be GB followed by 9 digits.")
    return tax_id[2:]

def get_open_obligations(company):
    h = {}
    h.update(accept_header)
    h.update(get_fraud_prevention_headers())

    oauth = get_session(company)
    vrn = get_vrn(company)
    api_base = frappe.db.get_single_value("HMRC API Settings", "api_base")
    response = oauth.get(
        api_base+"/organisations/vat/%s/obligations?status=O" % vrn,
            headers=h).json()
    if "obligations" not in response:
        frappe.throw("Message from HMRC: " + response["message"],
                     "Error retrieving obligations")
    return response["obligations"]

def submit_return(company, vat_return):
    oauth = get_session(company)
    vrn = get_vrn(company)
    api_base = frappe.db.get_single_value("HMRC API Settings", "api_base")
    response = oauth.post(api_base+"/organisations/vat/%s/returns" % vrn,
            headers = accept_header, json = vat_return)

    return response.json(), response.headers

@frappe.whitelist()
def fraud_prevention_header_feedback(company):
    oauth = get_session(company)
    api_base = frappe.db.get_single_value("HMRC API Settings", "api_base")
    response = oauth.get(
        api_base+"/test/fraud-prevention-headers/vat-mtd/validation-feedback",
        headers=accept_header)
    return response.json()

def get_session(company: str):
    app_name = frappe.get_single_value("HMRC API Settings", "connected_app")
    if not app_name:
        frappe.throw("No Connected App configured in HMRC API Settings")
    app = frappe.get_doc("Connected App", app_name)
    return app.get_oauth2_session(frappe.session.user)

@frappe.whitelist()
def mark_success(name: str):
    """Mark the HMRC Authorisation as successful, after OAuth callback.
    (Putting it in HMRC Authorisations doesn't work because of a VARCHAR limit
    on Success URI.)
    """
    hmrc_auth = frappe.get_doc("HMRC Authorisations", name)
    if hmrc_auth:
        hmrc_auth.set("authorisation_status", "Authorised")
        hmrc_auth.save()
        frappe.db.commit()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = hmrc_auth.get_url()
    else:
        frappe.throw("HMRC Authorisation not found")