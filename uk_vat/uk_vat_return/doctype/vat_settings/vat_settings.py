# Copyright (c) 2025, Software to Hardware Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VATSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from uk_vat.uk_vat_return.doctype.place_of_supply_rules.place_of_supply_rules import PlaceofSupplyRules
		from uk_vat.uk_vat_return.doctype.vat_account_mappings.vat_account_mappings import VATAccountMappings
		from uk_vat.uk_vat_return.doctype.vat_rate_definitions.vat_rate_definitions import VATRateDefinitions

		company: DF.Link | None
		country: DF.Data | None
		default_purchase_tax_template: DF.Link | None
		default_sales_tax_template: DF.Link | None
		place_of_supply_rules: DF.Table[PlaceofSupplyRules]
		portal_api: DF.Literal["None", "UK MTD", "Estonia e-MTA"]
		return_frequency: DF.Literal["Monthly", "Quarterly", "Yearly"]
		vat_account_mappings: DF.Table[VATAccountMappings]
		vat_rate_definitions: DF.Table[VATRateDefinitions]
		vat_reg_no: DF.Data | None
	# end: auto-generated types

	pass

	@property
	def country(self) -> str | None:
		"""Returns the company's country code for the VAT settings."""
		if self.company:
			return frappe.get_value("Company", self.company, "country")
		return None
