# -*- coding: utf-8 -*-
# Copyright (c) 2020 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# from pydoc import doc

import uk_vat.uk_vat_return.hmrc_api.vat as vat_api
import uk_vat.vat.utils as vat_utils

from erpnext.controllers.taxes_and_totals import get_itemised_tax

import frappe
from frappe.model.document import Document
from frappe.types import DF
from frappe.utils import flt, get_link_to_form
import datetime
import urllib.parse

vat_return_schema = {
									# Box Number, Source of value, Description, Precision
	"vatDueSales":                  [1, "vat", "VAT due on sales", 2],
	"vatDueAcquisitions":           [2, "vat", "VAT due on EU acquisitions", 2],
	"totalVatDue":                  [3, None, "Total VAT due", 2],
	"vatReclaimedCurrPeriod":       [4, "vat", "VAT reclaimed on purchase", 2],
	"netVatDue":                    [5, None, "Net VAT", 2],
	"totalValueSalesExVAT":         [6, "base_amount", "Total sales, ex. VAT", 0],
	"totalValuePurchasesExVAT":     [7, "base_amount", "Total purchases, ex. VAT", 0],
	"totalValueGoodsSuppliedExVAT": [8, "base_amount", "Total EC supply of goods, ex VAT", 0],
	"totalAcquisitionsExVAT":       [9, "base_amount", "Total EC acquisitions of goods, ex. VAT", 0]
}

class UKVATReturn(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link
		hmrc_charge_reference_number: DF.Data | None
		hmrc_correlation_id: DF.Data | None
		hmrc_form_bundle_number: DF.Data | None
		hmrc_payment_indicator: DF.Data | None
		hmrc_period_key: DF.Data | None
		hmrc_processing_date: DF.Data | None
		hmrc_receipt_id: DF.Data | None
		hmrc_receipt_timestamp: DF.Data | None
		hmrc_vrn: DF.Data | None
		is_finalised: DF.Check
		period_end_date: DF.Date
		period_start_date: DF.Date
		submitted_date: DF.Date | None
		total_ec_goods_input: DF.Currency
		total_ec_goods_output: DF.Currency
		total_input_exvat: DF.Currency
		total_output_exvat: DF.Currency
		vat_due_total: DF.Currency
		vat_eu_acquisitions: DF.Currency
		vat_input: DF.Currency
		vat_net: DF.Currency
		vat_output: DF.Currency
	# end: auto-generated types

	def before_save(self):
		# Prefer new generic GL-based computation if VAT Settings present
		box_values = {}
		country = frappe.get_value("Company", self.company, "country")
		try:
			box_values, _ = vat_utils.compute_vat_boxes_gl(
				self.company,
				self.period_start_date,
				self.period_end_date,
				country=country
			)
		except Exception:
			# Silent fallback to legacy method
			box_values = {}

		if box_values:
			# Map UK box codes to legacy field names (kept for compatibility)
			self.vat_output = box_values.get("1", 0)
			self.vat_eu_acquisitions = box_values.get("2", 0)
			self.vat_due_total = box_values.get("3", self.vat_output + self.vat_eu_acquisitions)
			self.vat_input = box_values.get("4", 0)
			self.vat_net = box_values.get("5", abs(self.vat_due_total - self.vat_input))
			self.total_output_exvat = box_values.get("6", 0)
			self.total_input_exvat = box_values.get("7", 0)
			self.total_ec_goods_output = box_values.get("8", 0)
			self.total_ec_goods_input = box_values.get("9", 0)
			return

		# Legacy path
		vat_return = self.get_vat_return() # self.period_start_date, self.period_end_date)

		# Box 1
		self.vat_output = vat_return["vatDueSales"]

		# Box 2
		self.vat_eu_acquisitions = vat_return["vatDueAcquisitions"]

		# Box 3
		self.vat_due_total = vat_return["totalVatDue"]

		# Box 4
		self.vat_input = vat_return["vatReclaimedCurrPeriod"]

		# Box 5
		self.vat_net = vat_return["netVatDue"]

		# Box 6
		self.total_output_exvat = vat_return["totalValueSalesExVAT"]

		# Box 7
		self.total_input_exvat = vat_return["totalValuePurchasesExVAT"]

		# Box 8
		self.total_ec_goods_output = vat_return["totalValueGoodsSuppliedExVAT"]

		# Box 9
		self.total_ec_goods_input = vat_return["totalAcquisitionsExVAT"]

	@frappe.whitelist()
	def get_open_obligations(self, **kwargs):
		frappe.log(f"Fetching open obligations from HMRC for {self.company}")
		h = {}
		h.update(vat_api.accept_header)
		h.update(vat_api.get_fraud_prevention_headers())

		oauth = vat_api.get_session(self.company)
		vrn = self.get_vrn()
		api_host = frappe.get_doc("HMRC API Settings").api_hostname
		address = f"https://{api_host}/organisations/vat/{vrn}/obligations"
		response = oauth.get(address, headers=h, params={"status": "O"}).json()
		if "obligations" not in response:
			frappe.throw("Message from HMRC: " + response["message"],
						"Error retrieving obligations")
		return response["obligations"]

	def get_erpnext_transactions(self, invoice_type: DF.Literal["Sales", "Purchase"]):

		doctype = f"{invoice_type} Invoice"
		docs = frappe.get_all(
			doctype, filters=[
				["company", "=", self.company],
				["docstatus", "=", 1],
				["posting_date", "between", [self.period_start_date, self.period_end_date]],
			]
		)
		txns = []
		for d in docs:
			doc = frappe.get_doc(doctype, d)
			doc_tax_detail = get_itemised_tax(doc.taxes, with_tax_account=True)
			txns.append({ doc.name: doc_tax_detail })

		# Format: { <invoice_id>: {
		#				<item_code> : {
		#					<account> : {
		#						'net_amount': <amount>,
		#                       'tax_account': <account>,
		#						'tax_amount': <amount>,
		#						'tax_rate': <rate>
		#					}
		#				}
		#			}
		return txns

	def get_transactions(self, invoice_type: DF.Literal["Sales", "Purchase"]):

		transactions = frappe.db.sql(f"""
			SELECT
				invoice.name as name,
				ii.item_name,
				ii.item_code,
				ii.idx,
				ii.base_amount,
				ii.item_tax_template,
				itd.tax_rate,
				tt.vat_transaction_type,
				tt.vat_treatment
			FROM 
				`tab{invoice_type} Invoice` invoice
			INNER JOIN
				`tab{invoice_type} Invoice Item` ii
			ON
				ii.parent = invoice.name

			INNER JOIN
				`tabItem Tax Template` tt
			ON
				tt.name = ii.item_tax_template

			LEFT JOIN
				`tabItem Tax Template Detail` itd
			ON
				itd.parent = tt.name

			WHERE
				invoice.docstatus = 1
			AND invoice.company = '{self.company}'
			AND invoice.posting_date >= '{self.period_start_date}'
			AND invoice.posting_date <= '{self.period_end_date}'
			""", as_dict=True)

		if not transactions:
			frappe.msgprint("No transactions found.")
			return []

		# Calculate the VAT for each line
		for t in transactions:
			if t["item_tax_template"] is None:
				frappe.throw(
					"Item Tax Template not set on one of the lines in invoice %s" %
					t["name"])
			if t["vat_rate"] is None:
				frappe.throw("VAT rate not set on Item Tax Template %s" %
					t["item_tax_template"])

			t["vat"] = t["base_amount"] * (t["vat_rate"] / 100.0)

		return transactions


	def get_vat_return(self, drilldown=None):

		if self.period_start_date > self.period_end_date:
			frappe.throw("Cannot create VAT return where start date is after the end date.")

		# VAT return as required by UK Government API (HMRC).
		vat_return = {k: 0.0 for k in vat_return_schema}
		vat_return["finalised"] = False

		# If requested, initialise drilldown
		if drilldown is not None:
			for k in vat_return_schema:
				drilldown[k] = []

		# We centralise all changes to the VAT return so we can record the source
		# of each change.
		def increment(item, field_list):
			for field in field_list:
				amount = item[vat_return_schema[field][1]]
				vat_return[field] += amount
				if drilldown is not None:
					drilldown[field] += [[item, amount]]

		#
		# SALES (Output VAT)
		#
		for sale in self.get_transactions("Sales"):
			
			# EU rules
			if sale["vat_rules"]=="EU":

				if sale["vat_transaction_type"]=="Goods":
					# Boxes 6 and 8
					increment(sale, ("totalValueSalesExVAT", "totalValueGoodsSuppliedExVAT"))
				elif sale["vat_transaction_type"]=="Services":
					# Box 6
					increment(sale, ("totalValueSalesExVAT",))
				else:
					frappe.throw(
						"Unsupported vat_transaction_type '%s' for EU rules" % 
						repr(sale["vat_transaction_type"]))

			# UK trade
			elif sale["vat_rules"]=="Domestic":

				# Boxes 1 and 6
				increment(sale, ("vatDueSales","totalValueSalesExVAT"))
			
			# RoW
			elif sale["vat_rules"]=="Rest of World":

				if sale["vat_transaction_type"]=="Goods" or \
				sale["vat_transaction_type"]=="Services":
					# Box 6
					increment(sale, ("totalValueSalesExVAT",))
				else:
					frappe.throw(
						"Unsupported vat_transaction_type '%s' for RoW rules" % 
						repr(sale["vat_transaction_type"]))

			else:
				frappe.throw("Unknown vat_rules: %s" % repr(sale["vat_rules"]))

		#
		# Purchases (Input VAT)
		#
		for purchase in self.get_transactions("Purchase"):
			
			# EU rules
			if purchase["vat_rules"]=="EU":

				if purchase["vat_transaction_type"]=="Goods":

					# Boxes 2, 4, 7 and 9
					increment(purchase, 
						("vatDueAcquisitions", "vatReclaimedCurrPeriod",
						"totalValuePurchasesExVAT","totalAcquisitionsExVAT"))

				elif purchase["vat_transaction_type"]=="Services":

					# Boxes 1, 4, 6 and 7
					increment(purchase,
						("vatDueSales", "vatReclaimedCurrPeriod", 
						"totalValueSalesExVAT", "totalValuePurchasesExVAT"))

				else:
					frappe.throw(
						"Unsupported vat_transaction_type '%s' for EU rules" % 
						repr(purchase["vat_transaction_type"]))

			# UK trade
			elif purchase["vat_rules"]=="Domestic":

				if purchase["vat_is_reverse_charge"]:

					# Boxes 1, 4, 6 and 7
					increment(purchase,
						("vatDueSales", "vatReclaimedCurrPeriod", 
						"totalValueSalesExVAT", "totalValuePurchasesExVAT"))

				else:

					# Boxes 4 and 7
					increment(purchase,
						("vatReclaimedCurrPeriod", "totalValuePurchasesExVAT"))
		
			# RoW
			elif purchase["vat_rules"]=="Rest of World":

				if purchase["vat_transaction_type"]=="Goods":

					# Boxes 4 and 7
					increment(purchase,
						("vatReclaimedCurrPeriod", "totalValuePurchasesExVAT"))

				elif purchase["vat_transaction_type"]=="Services":

					# Boxes 1, 4, 6 and 7
					increment(purchase,
						("vatDueSales", "vatReclaimedCurrPeriod", 
						"totalValueSalesExVAT", "totalValuePurchasesExVAT"))

			
			else:
				frappe.throw("Unknown vat_rules: %s" % repr(purchase["vat_rules"]))

		# Box 3 = Box 1 + Box 2
		vat_return["totalVatDue"] += vat_return["vatDueSales"] + \
			vat_return["vatDueAcquisitions"]

		# Box 5 = |Box 3 - Box 4|
		vat_return["netVatDue"] = abs(vat_return["totalVatDue"] -
			vat_return["vatReclaimedCurrPeriod"])

		# All figures need to be of required precision
		for f in vat_return_schema.keys():
			vat_return[f] = flt(vat_return[f], vat_return_schema[f][3])

		return vat_return

	def get_vrn(self) -> str:
		"""Get the VAT Registration Number for the specified company from the
		Company's tax_id field."""
		tax_id = frappe.db.get_value("Company", self.company, "tax_id")
		# Remove GB prefix, if provided
		if tax_id and tax_id.upper().startswith("GB"):
			tax_id = tax_id[2:]
		# Validate tax_id
		if not tax_id or len(tax_id) != 9 or not tax_id.isdigit():
			link = get_link_to_form("Company", self.company)
			frappe.throw("Company Tax ID is invalid. It should be 9 digits. " \
						f"Please check the Tax ID for company {link}.")
		return tax_id


	@frappe.whitelist()
	def submit_vat_return(self, is_finalised):

		# Match dates on the form to an open obgligation
		obligations = self.get_open_obligations()
		selected_obligation = {}
		print(type(self.period_end_date))
		for o in obligations:
			start = datetime.datetime.strptime(o["start"], "%Y-%m-%d").date()
			end = datetime.datetime.strptime(o["end"], "%Y-%m-%d").date()
			if self.period_start_date==start and self.period_end_date==end:
				selected_obligation = o
				break
		else:
			frappe.throw("The selected dates do not match any open HMRC obligations")

		# Generate submission document
		vat_return = {
			"vatDueSales": self.vat_output,
			"vatDueAcquisitions": self.vat_eu_acquisitions,
			"totalVatDue": self.vat_due_total,
			"vatReclaimedCurrPeriod": self.vat_input,
			"netVatDue": self.vat_net,
			"totalValueSalesExVAT": int(self.total_output_exvat),
			"totalValuePurchasesExVAT": int(self.total_input_exvat),
			"totalValueGoodsSuppliedExVAT": int(self.total_ec_goods_output),
			"totalAcquisitionsExVAT": int(self.total_ec_goods_input),
			"finalised": True if is_finalised else False,
			"periodKey": selected_obligation.get("periodKey")
		}

		# Submit return to HMRC
		response, headers = self.submit_return(vat_return)
		if response.get("errors"):
			frappe.throw("\n".join({e["message"] for e in response["errors"]}),
			title=response["message"])

		# Save response
		self.hmrc_correlation_id = headers["X-CorrelationId"]
		self.hmrc_receipt_id = headers["Receipt-ID"]
		self.hmrc_receipt_timestamp = headers["Receipt-Timestamp"]
		self.hmrc_period_key = selected_obligation["periodKey"]
		self.hmrc_processing_date = response.get("processingDate")
		self.hmrc_form_bundle_number = response.get("formBundleNumber")
		self.hmrc_payment_indicator = response.get("paymentIndicator")
		self.hmrc_charge_reference_number = response.get("chargeRefNumber")
		self.hmrc_vrn = self.get_vrn()
		self.is_finalised = is_finalised
		self.docstatus = 1
		self.save()

	def get_gl_vat_boxes(self):
		"""Helper endpoint for client drilldown (generic)."""
		country = frappe.get_value("Company", self.company, "country")
		boxes, drill = vat_utils.compute_vat_boxes_gl(
			self.company, self.period_start_date, self.period_end_date, country=country
		)
		return {"boxes": boxes, "drill": drill}

	def submit_return(self, vat_return):
		oauth = vat_api.get_session(self.company)
		vrn = self.get_vrn()
		api_host = frappe.get_doc("HMRC API Settings").api_hostname
		response = oauth.post(
			f"https://{api_host}/organisations/vat/{vrn}/returns",
			headers=vat_api.accept_header, json=vat_return)
		return response.json(), response.headers
