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

		api_base: DF.Data | None
		auth_base: DF.Data | None
		connected_app: DF.Link | None
		gov_ip_headers: DF.Check
		installation_guid: DF.Data | None
	# end: auto-generated types

	def before_save(self):

		# Generate installation guid for HMRC API
		if self.installation_guid is None or len(self.installation_guid) < 5:
			self.installation_guid = str(uuid.uuid4())

	@frappe.whitelist()
	def test_api(self):
		app = frappe.get_doc("Connected App", self.connected_app)
		app.get_backend_app_token(include_client_id=True)
		return "Success"
