# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    account_analytic_id = fields.Many2one('account.analytic.account',
        related="session_id.account_analytic_id",
        copy=False, store=True, string='Analytic Account')

    def _prepare_invoice_line(self, order_line):
        res = super(PosOrder, self)._prepare_invoice_line(order_line)
        if order_line.order_id.account_analytic_id.id:
            res['analytic_distribution'] = { order_line.order_id.account_analytic_id.id: 100}
        return res
