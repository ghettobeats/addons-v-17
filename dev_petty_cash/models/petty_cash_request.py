# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class petty_cash_request(models.Model):
    _name = 'petty.cash.request'
    _description = 'Solicitud de Reposicion Caja Chica'
    _order = 'name desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    @api.model
    def _get_request_by(self):
        employee_id =self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        return employee_id.id or False

    def _default_team_id(self):
        team_id = self.env['tipo.caja.chica'].search([('team_members', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['tipo.caja.chica'].search([], limit=1).id
        return team_id
    
    name = fields.Char('Nombre', default='/', tracking=1)
    tipo_caja_id = fields.Many2one('tipo.caja.chica', string='Tipo de Caja', default=_default_team_id, index=True)
    request_to = fields.Many2one('hr.employee', string='Solicitado A')
    request_by = fields.Many2one('hr.employee', string='Solicitado Por', default=_get_request_by)

    payment_journal_id = fields.Many2one('account.journal', string='Diario De Pago')
    petty_journal_id=  fields.Many2one('account.journal', string='Diario de Caja', tracking=2)

    date = fields.Date('Fecha', copy=False, default=fields.Datetime.now)
    request_amount = fields.Monetary('Monto Solicitado', tracking=2)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self:self.env.company.currency_id)
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self:self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self:self.env.company)

    state = fields.Selection(string='Estado', selection=[('draft', 'Borrador'),
                                                        ('request', 'Solicitado'),
                                                        ('approve', 'Aprobado'),
                                                        ('cancel','Cancelado'),
                                                        ('reject','Rechazado')], default='draft', tracking=4)
    payment_id = fields.Many2one('account.payment', string='Pago', copy=False)
    balance = fields.Monetary('Balance', compute='_get_balance')
    
    @api.depends('payment_id')
    def _get_balance(self):
        for request in self:
            balance = 0.0
            for line in self.env['account.move.line'].search(
                    [('account_id', '=', request.petty_journal_id.default_account_id.id),
                     ('move_id.state', '=', 'posted')]):
                balance += line.amount_currency
            request.balance = abs(balance)
                    
        
    
    
    def create_payment(self):
        payment_method_id= self.env['account.payment.method'].search([('name','=','Manual')],limit=1)
        if not payment_method_id:
            payment_method_id= self.env['account.payment.method'].search([],limit=1)

        pays = self.env['account.payment']

        if hasattr(pays, "destination_journal_id"):

            vals={
                'payment_type':'outbound',
                'partner_id':self.company_id.partner_id.id or False,
                'destination_account_id':self.petty_journal_id.default_account_id.id or False,
                'is_internal_transfer':True,
                'company_id':self.company_id and self.company_id.id or False,
                'amount':self.request_amount or 0.0,
                'currency_id':self.currency_id and self.currency_id.id or False,
                'journal_id':self.payment_journal_id and self.payment_journal_id.id or False,
    #            'payment_method_id':payment_method_id and payment_method_id.id or False,
                'destination_journal_id':self.petty_journal_id.id or False,
            }
        else:
            vals = {
                'payment_type': 'outbound',
                'partner_id': self.company_id.partner_id.id or False,
                'destination_account_id': self.petty_journal_id.default_account_id.id or False,
                'is_internal_transfer': True,
                'company_id': self.company_id and self.company_id.id or False,
                'amount': self.request_amount or 0.0,
                'amount_to_journal': self.request_amount or 0.0,
                'currency_id': self.currency_id and self.currency_id.id or False,
                'journal_id': self.payment_journal_id and self.payment_journal_id.id or False,
                #            'payment_method_id':payment_method_id and payment_method_id.id or False,
                'to_journal_id': self.petty_journal_id.id or False,
            }


        payment_id = self.env['account.payment'].sudo().create(vals)
        payment_id.action_post()
        self.payment_id= payment_id and payment_id.id or False
    
    def action_request(self):
        if self.request_amount <= 0:
            raise ValidationError(_('Request Amount must be positive.'))
        self.state='request'
    
    def action_approve(self):
        self.create_payment()
        self.state='approve'
    
    def action_cancel(self):
        self.state='cancel'
    
    def action_reject(self):
        self.state= 'reject'
    
    def action_draft(self):
        self.state = 'draft'
        
        
    def unlink(self):
        for request in self:
            if request.state != 'draft':
                raise ValidationError(_("You can delete Petty request in draft state only."))
        return super(petty_cash_request, self).unlink()
        
    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('petty.cash.request') or '/',
			
        })
        return super(petty_cash_request, self).create(vals)

#class account_payment(models.Model):
#    _inherit='account.payment'
#    
#    @api.model
#    def create(self,vals):
#        res = super(account_payment,self).create(vals)
#        return res        

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
