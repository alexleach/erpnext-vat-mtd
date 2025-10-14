# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import uuid

class HMRCAPISettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		connected_app: DF.Link | None
		gov_ip_headers: DF.Check
		installation_guid: DF.Data | None
		is_sandbox_app: DF.Check
	# end: auto-generated types

	def before_save(self):
		# Generate installation guid for HMRC API
		if self.installation_guid is None or len(self.installation_guid) < 5:
			self.installation_guid = str(uuid.uuid4())

	@frappe.whitelist()
	def create_app(self):
		"""Create the Connected App if it does not already exist"""
		if self.connected_app:
			frappe.msgprint("Connected App already exists")
			return
		app = frappe.new_doc("Connected App")
		app.provider_name = "UK HMRC VAT"
		app = self.update_app(app=app)
		self.connected_app = app.name
		self.save()

	def update_app(self, app=None):
		"""Update the Connected App with the required settings"""
		if app is None:
			if not self.connected_app:
				frappe.throw("Please set the Connected App first")
			app = frappe.get_doc("Connected App", self.connected_app)
		app.set("scopes", [])
		app.append("scopes", {"scope": "read:vat"})
		app.append("scopes", {"scope": "write:vat"})
		domain = "api.service.hmrc.gov.uk"
		if self.is_sandbox_app:
			domain = "test-" + domain
		app.authorization_uri = f"https://{domain}/oauth/authorize"
		app.token_uri = f"https://{domain}/oauth/token"
		app.save()
		return app

	def validate(self):
		# Update the app in case the sandbox setting has changed
		self.update_app()

	@frappe.whitelist()
	def test_api(self):
		import oauthlib.oauth2.rfc6749.errors
		app = frappe.get_doc("Connected App", self.connected_app)
		try:
			app.get_backend_app_token(include_client_id=True)
		except oauthlib.oauth2.rfc6749.errors.InvalidClientError:
			app_link = frappe.utils.get_link_to_form("Connected App", app.name, label=app.provider_name)
			msg = ("The Connected App settings appear to be incorrect. "
				"In particular, please check the Client ID and Client Secret "
				f"in the Connected App {app_link} are correct.")
			frappe.throw(msg)
		return "Successfully obtained a token from HMRC!"
