'''
Created on Oct 20, 2019

@author: Zuhair Hammadi
'''
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.fields import Command

class PaymentAllocation(models.TransientModel):
    _name = "account.payment.allocation"
    _description ='Payment Allocation'
    
    @api.model
    def _get_payment(self):
        if self._context.get('active_model') == 'account.payment':
            return [(6,0, self._context.get('active_ids'))]
        
    @api.model
    def _get_invoice(self):
        if self._context.get('active_model') == 'account.move':
            return [(6,0, self._context.get('active_ids'))]
        
    def _get_move_line_ids(self):
        if self._context.get('active_model') == 'account.move.line':
            return [(6,0, self._context.get('active_ids'))]        
        
    @api.model
    def _get_currency_id(self):
        currency_id = self.env['res.currency']
        
        if self._context.get('active_model') == 'account.move':
            currency_id = self.env['account.move'].browse(self._context.get('active_ids')).mapped('currency_id')
            
        elif self._context.get('active_model') == 'account.payment':
            currency_id = self.env['account.payment'].browse(self._context.get('active_ids')).mapped('currency_id')
                
        currency_id -= self.env.company.currency_id
        if len(currency_id)==1:
            return currency_id            
        
        return self.env.company.currency_id        
    
    partner_id = fields.Many2one('res.partner')
    account_id = fields.Many2one('account.account', required = True)
    show_child = fields.Boolean('Show parent/children')    
    
    line_ids = fields.One2many('account.payment.allocation.line', 'allocation_id')
    debit_line_ids = fields.One2many('account.payment.allocation.line', 'allocation_id', domain = [('type', '=', 'debit')])
    credit_line_ids = fields.One2many('account.payment.allocation.line', 'allocation_id', domain = [('type', '=', 'credit')])
    
    company_id = fields.Many2one('res.company', required = True, default = lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', required = True, default = _get_currency_id)
    
    balance = fields.Monetary(compute ='_calc_balance')
    
    payment_ids = fields.Many2many('account.payment', default = _get_payment)
    invoice_ids = fields.Many2many('account.move', default = _get_invoice)
    move_line_ids = fields.Many2many('account.move.line', default = _get_move_line_ids)
    
    writeoff_journal_id = fields.Many2one('account.journal', string='Write off Journal')
    writeoff_ref = fields.Char('Write off Reference')
    writeoff_line_ids = fields.One2many('account.payment.allocation.writeoff','allocation_id')
    
    create_entry = fields.Boolean('Create Account/Partner Entry')
    entry_journal_id = fields.Many2one('account.journal', string='Account/Partner Entry Journal')
    entry_name = fields.Char('Entry Reference')
    
    date_from = fields.Date()
    date_to = fields.Date()
    
    ref = fields.Char('Reference')
    
    max_date = fields.Date(compute = '_calc_max_date')
    manual_currency_rate = fields.Binary(compute = '_calc_manual_currency_rate')
    
    @api.depends('debit_line_ids.allocate', 'credit_line_ids.allocate', 'line_ids.allocate')
    def _calc_max_date(self):
        for record in self:                   
            line_ids = self.line_ids | self.debit_line_ids | self.credit_line_ids
            record.max_date = max(line_ids.filtered('allocate').mapped('move_line_id.date') or [fields.Date.today()])            
            
    @api.depends('debit_line_ids.allocate', 'credit_line_ids.allocate', 'line_ids.allocate')            
    def _calc_manual_currency_rate(self):        
        if 'currency_rate' not in self.env['account.payment']:
            self.manual_currency_rate  = False
            return
                
        manual_currency_rate = {}
        line_ids = self.line_ids | self.debit_line_ids | self.credit_line_ids
        
        payment_line_ids = line_ids.filtered(lambda line : line.allocate and line.payment_id and line.move_currency_id != line.company_currency_id) 
        for line in payment_line_ids:    
            payment = line.payment_id            
            if payment.currency_rate:
                manual_currency_rate[payment.currency_id.id] = payment.currency_rate
                
        if not payment_line_ids:
            refund_line_ids = line_ids.filtered(lambda line : line.allocate and line.invoice_id.move_type in ['in_refund', 'out_refund'] and line.move_currency_id != line.company_currency_id)
            for line in refund_line_ids:
                refund = line.invoice_id            
                if refund.currency_rate:
                    manual_currency_rate[refund.currency_id.id] = refund.currency_rate
                    
                    
        self.manual_currency_rate = manual_currency_rate
    
    @api.model
    def default_get(self, fields_list):
        if self._context.get("active_model") == 'account.move' and self.env['ir.config_parameter'].sudo().get_param('payment.allocation.invoice_disabled') == 'True' :
            invoice = self.env['account.invoice'].browse(self._context.get('active_id'))
            if invoice.move_type not in ['out_refund', 'in_refund']:
                raise UserError(_("Please use allocation from payment / credit notes"))
            
        return super(PaymentAllocation, self).default_get(fields_list)
    
    
    def _check_move_line_ids(self):
        company = None
        account = None
        for line in self.move_line_ids:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.account_type not in ('asset_cash', 'liability_credit_card'):
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))
            
    
    @api.onchange('move_line_ids')
    def _onchange_move_line_ids(self):
        if self.move_line_ids:
            self._check_move_line_ids()            
            
            self.company_id = self.move_line_ids.company_id
            self.account_id = self.move_line_ids.account_id

            if len(self.move_line_ids.partner_id) == 1:
                self.partner_id = self.move_line_ids.partner_id
                
            if len(self.move_line_ids.currency_id) == 1:
                self.currency_id = self.move_line_ids.currency_id
                                            
        
    @api.onchange('account_id', 'partner_id', 'show_child', 'company_id', 'currency_id', 'date_from', 'date_to', 'ref', 'move_line_ids')
    def _reset_lines(self):
        if not self.account_id:
            return
        
        self.debit_line_ids = False
        self.credit_line_ids = False
        
        domain = [('account_id', '=', self.account_id.id), ('reconciled', '=', False), ('company_id', '=', self.company_id.id), ('parent_state','=', 'posted')]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
    
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
            
        if self.ref:
            domain.append(('ref', 'ilike', self.ref))
        
        if self.partner_id:
            if self.show_child:
                partner_id = self.partner_id
                while partner_id.parent_id:
                    partner_id = partner_id.parent_id
                domain.append(('partner_id', 'child_of', partner_id.ids))
            else:
                domain.append(('partner_id', '=', self.partner_id.id))                                
            
        move_lines = self.env['account.move.line'].search(domain, order = 'date_maturity,date,move_name,id')
        for move_line in move_lines:
            line_type = 'debit' if move_line.debit else 'credit'
            fname = f"{line_type}_line_ids"
            allocate = move_line.payment_id in self.payment_ids._origin or move_line.move_id in self.invoice_ids._origin or move_line in self.move_line_ids._origin
            
            new_line = self[fname].new({
                'move_line_id' : move_line.id,
                'allocate' : allocate,
                'type' : line_type,
                })
            self[fname] += new_line
            new_line._calc_allocate_amount()
            
    @api.onchange('writeoff_line_ids')
    def _onchange_writeoff_line_ids(self, force_update = False):
        in_draft_mode = self != self._origin
        
        def need_update():
            amount = 0
            for line in self.writeoff_line_ids:
                if line.auto_tax_line:
                    amount -= line.balance
                    continue
                if line.tax_ids:
                    balance_taxes_res = line.tax_ids._origin.compute_all(
                        line.balance,
                        currency=line.currency_id,
                        quantity=1,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=False,
                        handle_price_include=True,
                    )
                    for tax_res in balance_taxes_res.get("taxes"):
                        amount += tax_res['amount']
            return amount 
        
        if not force_update and not need_update():
            return
        
        to_remove = self.env['account.payment.allocation.writeoff']        
        if self.writeoff_line_ids:
            for line in list(self.writeoff_line_ids):
                if line.auto_tax_line:
                    to_remove += line
                    continue
                if line.tax_ids:
                    balance_taxes_res = line.tax_ids._origin.compute_all(
                        line.balance,
                        currency=line.currency_id,
                        quantity=1,
                        product=line.product_id,
                        partner=line.partner_id,
                        is_refund=False,
                        handle_price_include=True,
                    )
                    for tax_res in balance_taxes_res.get("taxes"):
                        create_method = in_draft_mode and line.new or line.create
                        create_method({
                            'allocation_id' : self.id,
                            'account_id' : tax_res['account_id'],
                            'name' : tax_res['name'],
                            'balance' : tax_res['amount'],
                            'tax_repartition_line_id' : tax_res['tax_repartition_line_id'],
                            'tax_tag_ids' : tax_res['tag_ids'],
                            'auto_tax_line' : True,
                            'sequence' : line.sequence,

                            })
            
            if in_draft_mode:
                self.writeoff_line_ids -=to_remove
            else:
                to_remove.unlink()
            
                                                            
    @api.onchange('payment_ids')         
    def _onchange_payment_ids(self):
        if self.payment_ids:
            self.account_id = self.payment_ids[0].destination_account_id
            self.partner_id = self.payment_ids[0].partner_id
            self._reset_lines()
            
    @api.onchange('invoice_ids')         
    def _onchange_invoice_ids(self):
        if self.invoice_ids:
            self.account_id = self.invoice_ids.line_ids.filtered(lambda line : not line.reconciled and line.account_id.reconcile).account_id[:1]
            self.partner_id = self.invoice_ids[0].partner_id
            self._reset_lines()
    
    @api.onchange('writeoff_journal_id')
    def _onchange_writeoff_journal_id(self):
        if self.writeoff_journal_id and not self.writeoff_ref:
            self.writeoff_ref = _('Write-Off')
                                    
    @api.depends('debit_line_ids.allocate_amount', 'credit_line_ids.allocate_amount', 'writeoff_line_ids.balance')
    def _calc_balance(self):
        for record in self:
            balance = 0
            for line in record.debit_line_ids + record.credit_line_ids:
                if line.allocate:
                    balance += line.allocate_amount * line.sign
            record.balance = balance + sum(record.mapped('writeoff_line_ids.balance'))
    
    def _prepare_exchange_diff_move(self, move_date):
        return {
            'move_type': 'entry',
            'date': move_date,
            'journal_id': self.company_id.currency_exchange_journal_id.id,
            'line_ids': [],
        }

    def validate(self):         
        if self.manual_currency_rate:
            self =  self.with_context(manual_currency_rate = self.manual_currency_rate)
                                            
        max_date = self.max_date
        
        if self.writeoff_journal_id and self.writeoff_line_ids:
            
            if self.currency_id != self.company_id.currency_id:
                currency_id = self.currency_id.id
                amount_currency = self.balance
                balance = self.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id, max_date)
            else:
                currency_id = False
                amount_currency = False
                balance = self.balance
                
            move_vals= {
                'journal_id' : self.writeoff_journal_id.id,
                'ref': self.writeoff_ref or _('Write-Off'),
                'date' : max_date,
                'line_ids' : [],
                'move_type' : 'entry',
                'partner_id' : self.partner_id.id
            }
            writeoff_total = 0
            for line in self.writeoff_line_ids:
                writeoff_total -= line.balance
                move_vals['line_ids'].append(Command.create({
                    'account_id' : line.account_id.id,
                    'currency_id' : line.currency_id.id,
                    'amount_currency' : -line.balance,
                    'partner_id' : line.partner_id.id,
                    'product_id' : line.product_id.id,
                    'name' : line.name,
                    'tax_ids' : [Command.set(line.tax_ids.ids)],
                    'tax_tag_ids' : [Command.set(line.tax_tag_ids.ids)],
                    'tax_repartition_line_id' : line.tax_repartition_line_id.id,           
                    'analytic_distribution' : line.analytic_distribution,
                    'display_type' : 'tax' if line.tax_repartition_line_id else 'product'         
                    }))
            
            move_vals['line_ids'].append(Command.create({
                'account_id' : self.account_id.id,
                'currency_id' : self.currency_id.id,
                'amount_currency' : -writeoff_total,
                'partner_id' : self.partner_id.id,        
                'display_type' : 'payment_term' if self.account_id.account_type in ['asset_receivable', 'liability_payable'] else 'product'        
                }))            
                                                
            move_id = self.env['account.move'].with_context(skip_invoice_sync = True).create(move_vals)
            move_id._post()                        
            
            move_line_id = move_id.line_ids.filtered(lambda line : line.account_id == self.account_id)
            
            line = self.env["account.payment.allocation.line"].create({
                'allocation_id' : self.id,
                'type' : 'debit' if move_line_id.debit else 'credit',
                'move_line_id' : move_line_id.id,
                'allocate' : True,
                })
            line.allocate_amount = line.amount_residual_display            
                       
        debit_line_ids = self.line_ids.filtered(lambda line : line.allocate and line.allocate_amount and line.move_line_id.debit)
        credit_line_ids = self.line_ids.filtered(lambda line : line.allocate and line.allocate_amount and line.move_line_id.credit)
        if not debit_line_ids or not credit_line_ids:
            raise UserError(_('Select at least one debit line and one credit line'))
            
        move_line_ids = (debit_line_ids + credit_line_ids).mapped('move_line_id')
                                    
        partner_ids = move_line_ids.mapped('partner_id')
        partner_balance = False
        if len(partner_ids) > 1 and self.create_entry:
            partner_balance = dict.fromkeys(partner_ids.ids, 0)
        
        partial_reconcile_ids = self.env["account.partial.reconcile"]
        
        line_currency_diff = {}
        
        for debit_line in debit_line_ids:
            for credit_line in credit_line_ids:
                allocate_amount = min (debit_line.allocate_amount, credit_line.allocate_amount)
                if not allocate_amount:
                    continue
                                                                                                        
                vals = {
                    'debit_move_id' : debit_line.move_line_id.id,
                    'credit_move_id' : credit_line.move_line_id.id,                    
                    'amount' : self.currency_id._convert(allocate_amount, self.company_id.currency_id, self.company_id, max_date),                    
                    'debit_amount_currency' : self.currency_id._convert(allocate_amount, debit_line.move_line_id.currency_id, self.company_id, max_date),
                    'credit_amount_currency' : self.currency_id._convert(allocate_amount, credit_line.move_line_id.currency_id, self.company_id, max_date)
                    }
                                                
                for n in range(2):                                
                    for line, amount_currency, sign in [(debit_line,vals['debit_amount_currency'],1) , (credit_line,vals['credit_amount_currency'], -1)]:
                        if line.move_line_id.amount_currency:
                            rate = line.move_line_id.amount_currency / line.move_line_id.balance
                            old_amount = amount_currency / rate
                            diff_amount = self.company_id.currency_id.round((old_amount - vals['amount'])  * sign)                 
                            if n==0 and (diff_amount * sign) < 0:
                                vals['amount'] =  self.company_id.currency_id.round(vals['amount'] + (diff_amount * sign))
                            if n==1:  
                                line_currency_diff[line.move_line_id] = diff_amount                    
                    
                partial_reconcile_ids += self.env["account.partial.reconcile"].create(vals)
                if partner_balance:
                    partner_balance[debit_line.move_line_id.partner_id.id] += allocate_amount
                    partner_balance[credit_line.move_line_id.partner_id.id] -= allocate_amount
                
                debit_line.allocate_amount -= allocate_amount * (debit_line.allocate_amount < 0 and -1 or 1)
                credit_line.allocate_amount -= allocate_amount * (credit_line.allocate_amount < 0 and -1 or 1)            
        
        exchange_lines = []
        exchange_move = self.env['account.move']
        exchange_partial_reconcile = self.env["account.partial.reconcile"]
        exchange_lines_to_rec = self.env['account.move.line']

        for move_line in move_line_ids:
            if not move_line.amount_currency:
                continue
            if not move_line.amount_residual_currency and not move_line.amount_residual:
                continue
            
            if not move_line.amount_residual_currency and move_line.amount_residual:
                amount = move_line.amount_residual
            elif move_line in line_currency_diff:
                amount = line_currency_diff[move_line]
            else:
                amount = move_line.amount_residual - move_line.currency_id._convert(move_line.amount_residual_currency, self.company_id.currency_id, self.company_id, max_date)
            
            amount = self.company_id.currency_id.round(amount)
            if amount:
                exchange_lines.append((move_line, amount))      
                                
        if exchange_lines:
            exchange_move = self.env['account.move'].with_context(skip_invoice_sync = True).create(self._prepare_exchange_diff_move(move_date=max_date))
            exchange_journal = exchange_move.journal_id
            for move_line, amount in exchange_lines:
                line_to_rec = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync = True).create({
                    'name': _('Currency exchange rate difference'),
                    'debit' : -amount if amount < 0 else 0,
                    'credit' : amount if amount > 0 else 0, 
                    'account_id' : move_line.account_id.id,
                    'move_id' : exchange_move.id,
                    'partner_id': move_line.partner_id.id,
                    'amount_currency' : 0,
                    'currency_id' : move_line.currency_id.id
                    })
                
                account_id = amount > 0 and self.company_id.expense_currency_exchange_account_id.id or self.company_id.income_currency_exchange_account_id.id
                if "currency.exchange.account" in self.env:
                    curency_exchange_account_id = self.env['currency.exchange.account'].search([('currency_id','=', move_line.currency_id.id), ('journal_id','=',exchange_journal.id)])
                    if curency_exchange_account_id.account_id:
                        account_id = curency_exchange_account_id.account_id.id
                        
                exchange_lines_to_rec += line_to_rec
                self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync = True).create({
                    'name': _('Currency exchange rate difference'),
                    'debit' : amount if amount > 0 else 0, 
                    'credit' : -amount if amount < 0 else 0,
                    'account_id': account_id,
                    'move_id': exchange_move.id,
                    'partner_id': move_line.partner_id.id,
                    'amount_currency' : 0,
                    'currency_id' : move_line.currency_id.id                    
                    })
                exchange_partial_vals = {
                    'debit_move_id' : line_to_rec.id if line_to_rec.debit else move_line.id,
                    'credit_move_id' : line_to_rec.id if line_to_rec.credit else move_line.id,
                    'amount' : abs(amount),
                    'debit_amount_currency' : 0,
                    'credit_amount_currency' : 0,                    
                    }
                if (move_line.id == exchange_partial_vals['debit_move_id'] and move_line.credit) or (move_line.id == exchange_partial_vals['credit_move_id'] and move_line.debit):
                    exchange_partial_vals.update({
                        'amount' : -exchange_partial_vals['amount'],
                        'debit_move_id' : exchange_partial_vals['credit_move_id'],
                        'credit_move_id' : exchange_partial_vals['debit_move_id']
                        })
                    
                exchange_partial_reconcile += self.env["account.partial.reconcile"].create(exchange_partial_vals)
            exchange_move._post()
            partial_reconcile_ids.exchange_move_id = exchange_move
        
        reconciled_move_line_ids = move_line_ids.filtered('reconciled') + exchange_lines_to_rec
        if reconciled_move_line_ids:            
            partial_reconcile_ids = partial_reconcile_ids.filtered(lambda record : record.debit_move_id in reconciled_move_line_ids or record.credit_move_id in reconciled_move_line_ids) + exchange_partial_reconcile
            self.env["account.full.reconcile"].create({
                'partial_reconcile_ids' : [(6,0, partial_reconcile_ids.ids)],
                'reconciled_line_ids' : [(6,0, reconciled_move_line_ids.ids)],
                #'exchange_move_id' : exchange_move.id
                })                                    
        
        if partner_balance:
            move_vals= {
                'journal_id' : self.entry_journal_id.id,
                'ref': self.entry_name or 'Payment Allocation',
                'date' : max_date,
                'line_ids' : []
                }
            for partner_id, balance in partner_balance.items():
                if not balance:
                    continue

                if self.currency_id != self.company_id.currency_id:
                    currency_id = self.currency_id.id
                    amount_currency = balance
                    balance = self.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id, max_date)
                else:
                    currency_id = False
                    amount_currency = False
                
                move_vals['line_ids'].append((0,0, {
                    'account_id': self.account_id.id,
                    'name' : '',
                    'partner_id' : partner_id,
                    'credit' : balance > 0 and balance or 0,
                    'debit' : balance < 0 and -balance or 0,
                    'currency_id' : currency_id,
                    'amount_currency' : amount_currency
                    }))
            move_id=self.env['account.move'].with_context(skip_invoice_sync = True).create(move_vals)
            move_id._post()
            move_id.line_ids.reconcile()
            move_line_ids +=  move_id.line_ids   
        
        return {
            'type' : 'ir.actions.act_window_close'
            }
            
