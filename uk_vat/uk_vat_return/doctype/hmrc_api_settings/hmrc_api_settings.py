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

		connected_app: DF.Link
		gov_ip_headers: DF.Check
		installation_guid: DF.Data | None
		is_sandbox_app: DF.Check
	# end: auto-generated types

	def before_save(self):
		# Generate installation guid for HMRC API
		if self.installation_guid is None or len(self.installation_guid) < 5:
			self.installation_guid = str(uuid.uuid4())

	def validate(self):
	    """Check that the Connected App's settings are correct"""
	    app = frappe.get_doc("Connected App", self.connected_app)
	    
	    # Clear existing scopes
	    app.scopes = []
	    
	    # Add scopes as proper child table entries
	    app.append("scopes", {"scope": "read:vat"})
	    app.append("scopes", {"scope": "write:vat"})
	    
	    # Set domain based on sandbox setting
	    domain = "api.service.hmrc.gov.uk"
	    if self.is_sandbox_app:
	        domain = "test-" + domain
	    
	    app.authorization_url = f"https://{domain}/oauth/authorize"
	    app.token_uri = f"https://{domain}/oauth/token"
	    
	    app.save()

	@frappe.whitelist()
	def test_api(self):
		app = frappe.get_doc("Connected App", self.connected_app)
		app.get_backend_app_token(include_client_id=True)
		return "Success"
