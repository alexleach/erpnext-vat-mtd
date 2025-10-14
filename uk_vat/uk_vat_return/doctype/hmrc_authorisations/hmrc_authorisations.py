# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from urllib.parse import urljoin

class HMRCAuthorisations(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		authorisation_status: DF.Literal["New", "In progress", "Authorised", "Authorisation failed"]
		company: DF.Link
		is_vat: DF.Check
	# end: auto-generated types

	def get_connected_app(self):
		app_name = frappe.db.get_single_value("HMRC API Settings", "connected_app")
		return frappe.get_doc("Connected App", app_name)

	@frappe.whitelist()
	def authorize_access(self):
		app = self.get_connected_app()
		self.set("authorisation_status", "In progress")
		auth_url = app.initiate_web_application_flow(success_uri=self.get_success_url())
		return {"url": auth_url}

	def get_success_url(self):
		base_url = frappe.utils.get_url()
		callback_path = (
			"/api/method/uk_vat.uk_vat_return.hmrc_api.vat.mark_success?name=" + self.name
		)
		return urljoin(base_url, callback_path)
