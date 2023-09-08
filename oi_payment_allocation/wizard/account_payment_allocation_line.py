'''
Created on Oct 20, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api

class PaymentAllocationLines(models.TransientModel):
    _name = "account.payment.allocation.line"
    _description ='Payment Allocation Line'
    
    allocation_id = fields.Many2one('account.payment.allocation', required = True, ondelete='cascade')
    type = fields.Selection([('debit', 'Debit'), ('credit', 'Credit')], required = True)
    
    move_line_id = fields.Many2one('account.move.line', required = True, ondelete = 'cascade')
   
    company_currency_id = fields.Many2one(related='move_line_id.company_currency_id')
    move_currency_id = fields.Many2one('res.currency',compute = '_calc_move_currency_id')
    allocation_currency_id = fields.Many2one(related='allocation_id.currency_id')
        
    amount_residual = fields.Monetary(compute ='_calc_amount_residual', currency_field = 'allocation_currency_id')
    partner_id = fields.Many2one(related='move_line_id.partner_id')
    ref = fields.Char(related='move_line_id.ref', readonly = True)
    name = fields.Char(related='move_line_id.name', readonly = True)
    move_name = fields.Char(related='move_line_id.move_name', readonly = True)
    date_maturity = fields.Date(related='move_line_id.date_maturity', readonly = True)
    date = fields.Date(related='move_line_id.date', readonly = True)
        
    allocate = fields.Boolean()
    allocate_amount = fields.Monetary(currency_field = 'allocation_currency_id')
    
    payment_id = fields.Many2one(related='move_line_id.payment_id', readonly = True, string='Payment')
    move_id = fields.Many2one(related='move_line_id.move_id', readonly = True)
    balance = fields.Monetary(related='move_line_id.amount_currency', currency_field = 'move_currency_id')
    
    amount = fields.Monetary(compute = '_calc_amount', currency_field = 'move_currency_id')
    
    amount_residual_display = fields.Monetary(compute = '_calc_amount_residual_display', string='Unallocated Amount', currency_field = 'allocation_currency_id')
    
    sign = fields.Integer(compute = "_calc_sign")
    
    document_name = fields.Char(compute = '_calc_document_name')
    
    refund = fields.Boolean(compute = '_calc_refund')
    
    @api.depends('move_id.move_type')
    def _calc_refund(self):
        for record in self:
            record.refund = record.move_id.move_type in ['out_refund', 'in_refund']
    
    @api.depends('payment_id', 'move_id')
    def _calc_document_name(self):
        for record in self:
            record.document_name = record.payment_id.display_name or record.move_id.display_name
    
    @api.depends('move_line_id')
    def _calc_move_currency_id(self):
        for record in self:
            record.move_currency_id = record.move_line_id.currency_id or record.move_line_id.company_currency_id
    
    @api.depends('move_line_id', 'allocation_currency_id', 'allocation_id.line_ids.allocate')
    def _calc_amount_residual(self):

        manual_currency_rate = self.allocation_id.manual_currency_rate
                         
        for record in self:
            max_date = max(record.allocation_id.line_ids.filtered('allocate').mapped('move_line_id.date') or [fields.Date.today()])
            
            if record.allocation_currency_id == record.company_currency_id:
                record.amount_residual = record.move_line_id.amount_residual
            elif record.allocation_currency_id == record.move_currency_id:
                record.amount_residual = record.move_line_id.amount_residual_currency
            elif record.move_line_id.currency_id:
                record.amount_residual = record.move_currency_id.with_context(manual_currency_rate = manual_currency_rate)._convert(record.move_line_id.amount_residual_currency, record.allocation_currency_id, record.allocation_id.company_id, max_date)
            else:
                record.amount_residual = record.company_currency_id.with_context(manual_currency_rate = manual_currency_rate)._convert(record.move_line_id.amount_residual, record.allocation_currency_id, record.allocation_id.company_id, max_date)
                    
    @api.depends('type')
    def _calc_sign(self):
        for record in self:            
            record.sign = record.type =='debit' and 1 or -1
            
    @api.depends('sign','balance')
    def _calc_amount(self):
        for record in self:
            record.amount = record.balance * record.sign
                
    @api.depends('amount_residual','sign')
    def _calc_amount_residual_display(self):
        for record in self:
            record.amount_residual_display = record.amount_residual * record.sign
    
    @api.onchange('allocate','amount_residual_display')
    def _calc_allocate_amount(self):
        line_ids = self.allocation_id.debit_line_ids + self.allocation_id.credit_line_ids
        other_lines = line_ids.filtered(lambda line : line !=self and line.allocate)
        total = 0
        for line in other_lines:
            total += line.allocate_amount * line.sign 
        
        total = total * self.sign
        
        if total < 0:
            total = abs(total)
        else:
            total = 0
        
        if not self.allocate:
            self.allocate_amount = 0
        elif total:
            self.allocate_amount = min(self.amount_residual_display, total)
        else:
            self.allocate_amount = self.amount_residual_display
                        
    @api.onchange('allocate_amount')
    def _onchange_allocate_amount(self):
        self.allocation_id._calc_balance()
