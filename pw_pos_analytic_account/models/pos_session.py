# -*- coding: utf-8 -*-
from odoo import models, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    account_analytic_id = fields.Many2one('account.analytic.account',
        related="config_id.account_analytic_id",
        store=True, string='Analytic Account', copy=False
    )

    def _get_stock_expense_vals(self, exp_account, amount, amount_converted):
        res = super(PosSession, self)._get_stock_expense_vals(exp_account, amount, amount_converted)
        if self.company_id.anglo_saxon_accounting and self.account_analytic_id:
            res['analytic_distribution'] = { self.account_analytic_id.id: 100}
        return res

    def _get_stock_output_vals(self, out_account, amount, amount_converted):
        res = super(PosSession, self)._get_stock_output_vals(out_account, amount, amount_converted)
        if not self.company_id.anglo_saxon_accounting:
            res['analytic_distribution'] = { self.account_analytic_id.id: 100}
        return res

    def _prepare_line(self, order_line):
        res = super(PosSession, self)._prepare_line(order_line)
        res['analytic_distribution'] = { order_line.order_id.account_analytic_id.id: 100}
        return res

    def _get_sale_vals(self, key, amount, amount_converted):
        res = super(PosSession, self)._get_sale_vals(key, amount, amount_converted)
        res['analytic_distribution'] = { self.account_analytic_id.id: 100}
        return res

    def _get_invoice_receivable_vals(self, amount, amount_converted):
        res = super(PosSession, self)._get_invoice_receivable_vals(amount, amount_converted)
        res['analytic_distribution'] = { self.account_analytic_id.id: 100}
        return res
