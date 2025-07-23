# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit ='sale.order'
    
    sale_manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    sale_manual_currency_rate = fields.Float('Rate', digits=(12, 6))


    def _prepare_invoice(self):
        res = super(SaleOrder,self)._prepare_invoice()
        res.update({'manual_currency_rate_active':self.sale_manual_currency_rate_active,'manual_currency_rate':self.sale_manual_currency_rate})
        return res

    @api.constrains("sale_manual_currency_rate")
    def _check_sale_manual_currency_rate(self):
        for record in self:
            if record.sale_manual_currency_rate_active:
                if record.sale_manual_currency_rate == 0:
                    raise UserError(
                        _('Exchange Rate Field is required , Please fill that.'))
                is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param("bi_manual_currency_exchange_rate.inverted_rate")
                if is_inverted_rate:
                    if record.sale_manual_currency_rate <1 :
                        raise UserError(_('Exchange Rate must be greater than or equal to 1 .'))

    @api.onchange('sale_manual_currency_rate_active', 'currency_id')
    def check_currency_id(self):
        if self.sale_manual_currency_rate_active:
            if self.currency_id == self.company_id.currency_id:
                self.sale_manual_currency_rate_active = False
                raise UserError(
                    _('Company currency and Sale currency same, You can not add manual Exchange rate for same currency.'))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_product_price_context(self):
        result = super(SaleOrderLine, self)._get_product_price_context()
        result['manual_currency_rate_active'] = self.order_id.sale_manual_currency_rate_active
        result['manual_currency_rate'] = self.order_id.sale_manual_currency_rate
        return result

    
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        res = super(SaleAdvancePaymentInv,self)._create_invoice(order, so_line, amount)
        if order.sale_manual_currency_rate_active:
            res.write({'manual_currency_rate_active':order.sale_manual_currency_rate_active,'manual_currency_rate':order.sale_manual_currency_rate})
        return res

class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _compute_price(self, product, quantity, uom, date, currency=None):
        """Compute the unit price of a product in the context of a pricelist application.

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: pricelist currency (for the specific case where self is empty)

        :returns: price according to pricelist rule, expressed in pricelist currency
        :rtype: float
        """
        product.ensure_one()
        uom.ensure_one()

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        manual_currency_rate_active = product._context.get('manual_currency_rate_active')
        manual_currency_rate = product._context.get('manual_currency_rate')
        # Pricelist specific values are specified according to product UoM
        # and must be multiplied according to the factor between uoms
        product_uom = product.uom_id
        if product_uom != uom:
            convert = lambda p: product_uom._compute_price(p, uom)
        else:
            convert = lambda p: p

        if self.compute_price == 'fixed':
            new_price = convert(self.fixed_price)
            if manual_currency_rate_active:
                price = new_price * manual_currency_rate
            else:
                price = new_price
        elif self.compute_price == 'percentage':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            new_price = (base_price - (base_price * (self.percent_price / 100))) or 0.0
            if manual_currency_rate_active:
                price = new_price * manual_currency_rate
            else:
                price = new_price
        elif self.compute_price == 'formula':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            # complete formula
            price_limit = base_price
            new_price = (base_price - (base_price * (self.price_discount / 100))) or 0.0 * manual_currency_rate
            if manual_currency_rate_active:
                price = new_price * manual_currency_rate
            else:
                price = new_price
            if self.price_round:
                price = tools.float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price += convert(self.price_surcharge)

            if self.price_min_margin:
                price = max(price, price_limit + convert(self.price_min_margin))

            if self.price_max_margin:
                price = min(price, price_limit + convert(self.price_max_margin))
        else:  # empty self, or extended pricelist price computation logic
            if manual_currency_rate_active:
                self = self.with_context(manual_currency_rate_active=manual_currency_rate_active,manual_currency_rate=manual_currency_rate)
            price = self._compute_base_price(product, quantity, uom, date, currency)
        return price

    def _compute_base_price(self, product, quantity, uom, date, currency):
        """ Compute the base price for a given rule

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: pricelist currency

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        currency.ensure_one()

        manual_currency_rate_active = product._context.get('manual_currency_rate_active')
        manual_currency_rate = product._context.get('manual_currency_rate')

        rule_base = self.base or 'list_price'
        if rule_base == 'pricelist' and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(product, quantity,currency=self.base_pricelist_id.currency_id, uom=uom,date=date)
            src_currency = self.base_pricelist_id.currency_id

        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id

            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]
        else:  # list_price
            src_currency = product.currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]

        if src_currency != currency:

            if manual_currency_rate_active:
                is_inverted_rate = self.env['ir.config_parameter'].sudo().get_param("bi_manual_currency_exchange_rate.inverted_rate")
                if is_inverted_rate:
                    price = price / manual_currency_rate
                else:
                    price = price * manual_currency_rate
            else:
                price = src_currency._convert(price, currency, self.env.company, date, round=False)
        return price