# Copyright (c) 2025, Software to Hardware Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PlaceofSupplyRules(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		counterparty_region: DF.Literal["Domestic", "EU", "Non-EU"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		preferred_purchase_tax_template: DF.Link | None
		preferred_sales_tax_template: DF.Link | None
		treatment: DF.Literal["Standard", "Reverse Charge", "Zero", "Exempt", "Out-of-Scope"]
		vat_id_required: DF.Check
	# end: auto-generated types

	pass
