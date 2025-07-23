# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models,api, _
from odoo.exceptions import UserError, ValidationError

class ResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    normal_rate = fields.Boolean("Normal Rate",config_parameter='bi_manual_currency_exchange_rate.normal_rate')
    inverted_rate = fields.Boolean("Inverted Rate",config_parameter='bi_manual_currency_exchange_rate.inverted_rate')


    @api.onchange('normal_rate')
    def check_normal_rate(self):
        if self.normal_rate:
            self.inverted_rate = False 
    
    @api.onchange('inverted_rate')
    def check_inverted_rate(self):
        if self.inverted_rate:
            self.normal_rate = False
        


