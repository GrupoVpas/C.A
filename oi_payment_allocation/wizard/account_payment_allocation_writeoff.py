'''
Created on Nov 27, 2022

@author: Zuhair Hammadi
'''
from odoo import models, fields, api

class PaymentAllocationWriteOff(models.TransientModel):
    _name = "account.payment.allocation.writeoff"
    _inherit = ['analytic.mixin']    
    _description ='Payment Allocation Write off'
    _order = 'sequence,id'
    
    allocation_id = fields.Many2one('account.payment.allocation', required = True, ondelete='cascade')
    sequence = fields.Integer()
    currency_id = fields.Many2one(related='allocation_id.currency_id')
    company_id = fields.Many2one(related='allocation_id.company_id')        
    account_id = fields.Many2one('account.account', required = True, domain="[('deprecated', '=', False), ('company_id', '=', company_id),('is_off_balance', '=', False)]", check_company=True)
    name = fields.Char(string='Label')
    balance = fields.Monetary('Amount')
    partner_id = fields.Many2one('res.partner')
    product_id = fields.Many2one('product.product', string='Product')
    
    tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount", check_company=True)
    tax_repartition_line_id = fields.Many2one(comodel_name='account.tax.repartition.line',
        string="Originator Tax Distribution Line", ondelete='restrict', readonly=True,
        check_company=True,
        help="Tax distribution line that caused the creation of this move line, if any")    
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict',
        help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    
    auto_tax_line = fields.Boolean()
            
    
    @api.depends('product_id', 'account_id')
    def _compute_analytic_distribution2(self):
        for record in self:
            distribution = self.env['account.analytic.distribution.model']._get_distribution({
                'product_id': record.product_id.id,
                'product_categ_id': record.product_id.categ_id.id,
                'account_prefix': record.account_id.code,
                'company_id': record.company_id.id,
            })
            record.analytic_distribution = distribution or record.analytic_distribution
    
                                                                                            
    @api.onchange('balance')
    def _onchange_statement_line_id(self):
        if not self.balance:
            self.balance = -self.allocation_id.balance            

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id and not self.name:
            self.name = self.account_id.name
    