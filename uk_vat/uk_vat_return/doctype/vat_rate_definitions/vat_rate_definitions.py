# Copyright (c) 2025, Software to Hardware Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VATRateDefinitions(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Data | None
		effective_from: DF.Date | None
		effective_to: DF.Date | None
		item_tax_type: DF.Link | None
		label: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Percent
		supply_type: DF.Literal["Goods", "Services"]
	# end: auto-generated types

	pass
