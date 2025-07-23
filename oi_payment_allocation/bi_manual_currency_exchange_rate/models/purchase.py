# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api,_
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_round


class PurchaseOrder(models.Model):
	_inherit ='purchase.order'
	
	purchase_manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
	purchase_manual_currency_rate = fields.Float('Rate', digits=(12, 6))

	def _prepare_invoice(self):
		res = super(PurchaseOrder, self)._prepare_invoice()
		if self.purchase_manual_currency_rate_active:
			res.update({
				'manual_currency_rate_active': self.purchase_manual_currency_rate_active,
				'manual_currency_rate' : self.purchase_manual_currency_rate,
			})
		return res

	@api.constrains("purchase_manual_currency_rate")
	def _check_sale_manual_currency_rate(self):
		for record in self:
			if record.purchase_manual_currency_rate_active:
				if record.purchase_manual_currency_rate == 0:
					raise UserError(
						_('Exchange Rate Field is required , Please fill that.'))
				is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param("bi_manual_currency_exchange_rate.inverted_rate")
				if is_inverted_rate:
					if record.purchase_manual_currency_rate <1 :
						raise UserError(_('Exchange Rate must be greater than or equal to 1 .'))


	@api.onchange('purchase_manual_currency_rate_active', 'currency_id')
	def check_currency_id(self):
		if self.purchase_manual_currency_rate_active:
			if self.currency_id == self.company_id.currency_id:
				self.purchase_manual_currency_rate_active = False
				raise UserError(
					_('Company currency and Purchase currency same, You can not add manual Exchange rate for same currency.'))


class PurchaseOrderLine(models.Model):
	_inherit ='purchase.order.line'
	
	@api.depends('product_qty', 'product_uom', 'company_id','order_id.purchase_manual_currency_rate')
	def _compute_price_unit_and_date_planned_and_name(self):
		for line in self:
			if not line.product_id or line.invoice_lines or not line.company_id:
				continue
			params = {'order_id': line.order_id}
			seller = line.product_id._select_seller(
				partner_id=line.partner_id,
				quantity=line.product_qty,
				date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
				uom_id=line.product_uom,
				params=params)
			po_line_uom = line.product_uom or line.product_id.uom_po_id
			price_unit = line.env['account.tax']._fix_tax_included_price_company(
				line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
				line.product_id.supplier_taxes_id,
				line.taxes_id,
				line.company_id,
			)

			if seller or not line.date_planned:
				line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

			# If not seller, use the standard price. It needs a proper currency conversion.
			if not seller:
				unavailable_seller = line.product_id.seller_ids.filtered(
					lambda s: s.partner_id == line.order_id.partner_id)
				if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
					# Avoid to modify the price unit if there is no price list for this partner and
					# the line has already one to avoid to override unit price set manually.
					continue
				po_line_uom = line.product_uom or line.product_id.uom_po_id
				price_unit = line.env['account.tax']._fix_tax_included_price_company(
					line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
					line.product_id.supplier_taxes_id,
					line.taxes_id,
					line.company_id,
				)
				if line.order_id.purchase_manual_currency_rate_active:
					is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param("bi_manual_currency_exchange_rate.inverted_rate")
					if is_inverted_rate:
						price_unit = price_unit / line.order_id.purchase_manual_currency_rate
					else:
						price_unit = price_unit * line.order_id.purchase_manual_currency_rate
					
				else:
					price_unit = line.product_id.cost_currency_id._convert(
						price_unit,
						line.currency_id,
						line.company_id,
						line.date_order or fields.Date.context_today(line),
						False
					)
				line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))
				continue

			is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param(
				"bi_manual_currency_exchange_rate.inverted_rate")
			po_line_uom = line.product_uom or line.product_id.uom_po_id
			price_unit = line.env['account.tax']._fix_tax_included_price_company(
				line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
				line.product_id.supplier_taxes_id,
				line.taxes_id,
				line.company_id,
			)
			# price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, line.company_id) if seller else 0.0
			if is_inverted_rate:
				price_unit = line.product_id.standard_price
			else:
				price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
																					 line.product_id.supplier_taxes_id,
																					 line.taxes_id,
																					 line.company_id) if seller else 0.0

			# price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price, line.product_id.supplier_taxes_id, line.taxes_id, line.company_id) if seller else 0.0
			if line.order_id.purchase_manual_currency_rate_active:
				is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param("bi_manual_currency_exchange_rate.inverted_rate")
				if is_inverted_rate:
					price_unit = price_unit / line.order_id.purchase_manual_currency_rate
				else:
					price_unit = price_unit * line.order_id.purchase_manual_currency_rate

			else:
				price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order or fields.Date.context_today(line), False)
			price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))
			line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)
			line.discount = seller.discount or 0.0

			# record product names to avoid resetting custom descriptions
			default_names = []
			vendors = line.product_id._prepare_sellers({})
			product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
			default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
			for vendor in vendors:
				product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
				default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
			if not line.name or line.name in default_names:
				product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
				line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))


	
