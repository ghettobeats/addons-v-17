# -*- coding: utf-8 -*-
# (C) 2018 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'



    advanced_invoice_ids = fields.Many2many('account.move', string="Advanced Invoices",
        compute='_compute_stat_buttons_from_advance',
        help="Invoices whose journal items have been reconciled with these payments.")
    advanced_invoices_count = fields.Integer(string="# Advanced Invoices",
        compute="_compute_stat_buttons_from_advance")
    advanced_bill_ids = fields.Many2many('account.move', string="Reconciled Bills",
        compute='_compute_stat_buttons_from_advance',
        help="Invoices whose journal items have been reconciled with these payments.")
    advanced_bills_count = fields.Integer(string="# Reconciled Bills",
        compute="_compute_stat_buttons_from_advance")

    @api.depends('recovery_ids', 'stored_advance_residual')
    def _compute_stat_buttons_from_advance(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_payments = self.filtered('id')
        if not stored_payments:
            self.advanced_invoice_ids = False
            self.advanced_invoices_count = 0
            self.advanced_bill_ids = False
            self.advanced_bills_count = 0
            return

        self.env['account.move'].flush()
        self.env['account.move.line'].flush()
        self.env['account.partial.reconcile'].flush()

        self._cr.execute('''
                SELECT
                    payment.id,
                    ARRAY_AGG(DISTINCT move.invoice_id) AS invoice_ids,
                    invoice.move_type
                FROM account_payment payment
                JOIN account_payment_recovery move ON payment.id = move.payment_id
                JOIN account_move invoice ON invoice.id = move.invoice_id
                 WHERE payment.id IN %(payment_ids)s
                    AND invoice.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
                GROUP BY payment.id, invoice.move_type
            ''', {
            'payment_ids': tuple(stored_payments.ids)
        })
        query_res = self._cr.dictfetchall()
        self.advanced_invoice_ids = self.advanced_invoices_count = False
        self.advanced_bill_ids = self.advanced_bills_count = False
        for res in query_res:
            pay = self.browse(res['id'])
            if res['move_type'] in self.env['account.move'].get_sale_types(True):
                pay.advanced_invoice_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.advanced_invoices_count = len(res.get('invoice_ids', []))
            else:
                pay.advanced_bill_ids += self.env['account.move'].browse(res.get('invoice_ids', []))
                pay.advanced_bills_count = len(res.get('invoice_ids', []))

    def button_open_bills_advanced(self):
        ''' Redirect the user to the bill(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Advanced Bills"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.advanced_bill_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.advanced_bill_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.advanced_bill_ids.ids)],
            })
        return action

    def button_open_invoices_advanced(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Advanced Invoices"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.advanced_invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.advanced_invoice_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.advanced_invoice_ids.ids)],
            })
        return action

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        ''' Ensure the 'payment_method_id' field is not null.
        Can't be done using the regular 'required=True' because the field is a computed editable stored one.
        '''
        for pay in self:
            if not pay.payment_method_id and not pay.is_advance_payment and not pay.is_internal_transfer:
                raise ValidationError(_("Please define a payment method on your payment."))

    destination_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Destination Account',
        store=True, readonly=False,
        compute='_compute_destination_account_id',
        domain="['|',('user_type_id.name', 'in', ('Non-current Liabilities', 'Prepayments')),('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
        check_company=True,
        help="The payment's currency.")


    is_advance_payment = fields.Boolean('Es pago por adelantado?', store=True)
    recovery_ids = fields.One2many(
        'account.payment.recovery', 'payment_id',
        'Avances aplicados', readonly=True)
    advance_residual = fields.Monetary('Advance residual', compute='get_advance_residual', store=False)
    stored_advance_residual = fields.Monetary('Advance residual stored', related='advance_residual', store=True)
    assign_advance_manually = fields.Boolean('Asignar pago adelantado manualmente?', store=True)

    @api.onchange('recovery_ids')
    def onchange_manually_advance(self):
        for rec in self:
            advance = 0.0
            for move in rec.recovery_ids:
                if rec.assign_advance_manually == True:
                    advance += move.amount
            if round(advance,2) > rec.amount or advance < 0:
                raise UserError(_("El monto total compensado no puede ser mayor al avance o un numero negativo."))
            rec.advance_residual = rec.amount - advance

    @api.constrains('is_advance_payment', 'journal_id')
    def _check_is_advance_payment(self):
        if self.is_advance_payment != \
                self.journal_id.is_advance_payment:
            if self.is_advance_payment:
                raise ValidationError(
                    _('Please select an advance payment journal'))


    @api.depends('amount', 'recovery_ids.payment_id', 'state')
    def get_advance_residual(self):

        for pay in self:
            pay.advance_residual = pay.stored_advance_residual
            if pay.state == 'posted':
                applied_amount = 0.0

                found = False
                for recovery in pay.recovery_ids:
                    if pay.id == recovery.payment_id.id:

                        applied_amount += recovery.amount
                        found = True
                if applied_amount > 0.0 and pay.stored_advance_residual > 0.0 and found:
                    # pay.advance_residual -= applied_amount
                    if pay.stored_advance_residual == pay.amount:
                        pay.stored_advance_residual -= applied_amount
                    # raise UserError(_("%s", pay.stored_advance_residual - (pay.amount - applied_amount)))
                    if applied_amount + pay.stored_advance_residual != pay.amount:
                        applied_partial = pay.stored_advance_residual - (pay.amount - applied_amount)
                        pay.stored_advance_residual -= applied_partial

                elif not found:
                    pay.advance_residual = pay.amount
                # raise UserError(_("%s",pay.advance_residual))

    @api.onchange('payment_type', 'partner_type', 'partner_id', 'journal_id', 'is_advance_payment')
    def compute_change_destination_account_id(self):
        if self.is_advance_payment:
            if self.partner_type == 'customer':

                self.destination_account_id = \
                    self.partner_id.property_account_receivable_advance_id.id
                self.partner_type = 'customer'
            elif self.partner_type == 'supplier':

                self.destination_account_id = \
                    self.partner_id.property_account_payable_advance_id.id
                self.partner_type = 'supplier'

    @api.depends('payment_type', 'partner_type', 'partner_id', 'journal_id', 'is_advance_payment')
    def _compute_destination_account_id(self):
        if self.is_advance_payment:
            if self.partner_type == 'customer':
                self.destination_account_id = \
                    self.partner_id.property_account_receivable_advance_id.id
            elif self.partner_type == 'supplier':

                self.destination_account_id = \
                    self.partner_id.property_account_payable_advance_id
        else:
            super(AccountPayment, self)._compute_destination_account_id()

    def action_cancel(self):
        """ Forbids cancellation of payments having recoveries.
        """
        if self.filtered('recovery_ids'):
            raise UserError(_("You can't cancel a payment with recoveries."))
        return super(AccountPayment, self).action_cancel()
