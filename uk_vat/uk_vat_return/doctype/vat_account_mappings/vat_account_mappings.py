# Copyright (c) 2025, Software to Hardware Ltd and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class VATAccountMappings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		direction: DF.Literal["Output", "Input", "RC Output", "RC Input", "Deferred"]
		notes: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		return_box__line: DF.Literal[None]
	# end: auto-generated types

	pass
