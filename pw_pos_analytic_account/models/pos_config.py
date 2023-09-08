# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account', related="pos_config_id.account_analytic_id", readonly=False)
