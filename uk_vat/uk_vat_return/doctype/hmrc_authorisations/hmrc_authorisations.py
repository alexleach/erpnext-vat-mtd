# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import get_request_site_address, get_link_to_form
import requests_oauthlib as ro
import datetime
import json

class HMRCAuthorisations(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		authorisation_status: DF.Literal["New", "In progress", "Authorised", "Authorisation failed"]
		authorised_services: DF.Data | None
		client_id: DF.Data | None
		client_secret: DF.Password | None
		oauth_refresh_token: DF.Password | None
		oauth_state: DF.Data | None
		oauth_token: DF.Data | None
		last_authorised_date: DF.Datetime | None
	# end: auto-generated types
	
def get_redirect_uri():
	return get_request_site_address(True) + "?cmd=uk_vat.uk_vat_return.doctype.hmrc_authorisations.hmrc_authorisations.hmrc_callback"

@frappe.whitelist()
def authorize_access(name: str):

	hmrc_authorisation = frappe.get_doc("HMRC Authorisations", name)
	if not hmrc_authorisation:
		link = get_link_to_form("HMRC Authorisations")
		message = f"You must create and authorise company {name} with HMRC before you can use the HMRC API: "
		frappe.throw(message + link)

	api_settings = frappe.get_single("HMRC API Settings")
	client_id = api_settings.get("client_id")
	auth_base = str(api_settings.get("auth_base"))

	# Generate authorisation request
	scope = ["read:vat", "write:vat"] # TODO: hard coded VAT request
	oauth = ro.OAuth2Session(
		client_id,redirect_uri=get_redirect_uri(), scope=scope
	)
	authorization_url, state = oauth.authorization_url(auth_base+'/oauth/authorize')

	# Save state so we can match callback to this record
	hmrc_authorisation.set("authorisation_status", "In progress")
	hmrc_authorisation.set("oauth_state", state)
	hmrc_authorisation.save()

	return { "url": authorization_url }

@frappe.whitelist()
def hmrc_callback(code=None, state=None,
                  error=None, error_description=None, error_code=None):

	company_name = frappe.db.get_value(
		"HMRC Authorisations",
		filters={"oauth_state": state},
		fieldname="name"
	)
	if not company_name:
		frappe.throw("No HMRC Authorisations found for state: {0}".format(state))

	company = frappe.get_doc("HMRC Authorisations", str(company_name))

	if error:
		company.oauth_refresh_token = None
		company.authorisation_status = "Authorisation failed"
		company.authorised_services = None
		company.last_authorised_date = None
		company.save()

		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/desk#Form/HMRC Authorisations/{0}".format(company)
		frappe.msgprint("HMRC authorisation was NOT successful. %s" % error_description)
		return

	api_settings = frappe.get_single("HMRC API Settings")
	client_id = api_settings.get("client_id")
	client_secret = api_settings.get_password("client_secret")
	api_base = str(api_settings.get("api_base"))

	scope = ["read:vat", "write:vat"] # TODO: hard coded VAT request
	oauth = ro.OAuth2Session(client_id, redirect_uri=get_redirect_uri())

	token = oauth.fetch_token(
			api_base+'/oauth/token',
			authorization_response = "https://doesntmatter/?code=%s" % code,
			client_id=client_id,
			client_secret = client_secret,
			include_client_id=True)

	api_settings.set("oauth_token", json.dumps(token))
	api_settings.set("authorisation_status", "Authorised")
	api_settings.set("authorised_services", " ".join(token["scope"]))
	api_settings.set("last_authorised_date", datetime.datetime.now())
	api_settings.save()

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/desk#Form/HMRC Authorisations/{0}".format(company_name)
	frappe.msgprint("HMRC authorisation successful!")

def get_session(company: str):
	hmrc_authorisation = frappe.get_doc("HMRC Authorisations", company)
	if not hmrc_authorisation or hmrc_authorisation.authorisation_status != "Authorised":
		link = get_link_to_form("HMRC Authorisations", "New")
		message = f"You must create and authorise company {company} with HMRC before you can use the HMRC API: "
		frappe.throw(message + link)

	token = json.loads(hmrc_authorisation.oauth_token)

	api_settings = frappe.get_single("HMRC API Settings")
	client_id = api_settings.get("client_id")
	client_secret = api_settings.get_password("client_secret")
	api_base = str(api_settings.get("api_base"))

	extra = {
		'client_id': client_id,
		'client_secret': client_secret,
	}

	def token_updater(token):
		hmrc_authorisation.set("oauth_token", json.dumps(token))
		hmrc_authorisation.save()

	return ro.OAuth2Session(client_id,
						token=token,
						auto_refresh_kwargs=extra,
						auto_refresh_url=api_base+'/oauth/token',
						token_updater=token_updater)

