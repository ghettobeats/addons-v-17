# -*- coding: utf-8 -*-
# (C) 2018 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_account_payable_advance_id = fields.Many2one(
        'account.account', "Account Advance Payable",
        domain=[
            ('deprecated', '=', False),
        ])
    property_account_receivable_advance_id = fields.Many2one(
        'account.account', "Account Advance Receivable",
        domain=[
            ('deprecated', '=', False),
        ])

    advanced_incoming_ids = fields.Many2many('account.payment', string="Advance incoming payments",
                                            compute='_compute_stat_buttons_from_advance')
    advanced_incoming_count = fields.Integer(string="# Advance I/P",
                                             compute="_compute_stat_buttons_from_advance")
    advanced_outgoing_ids = fields.Many2many('account.payment', string="Advance outgoing payments",
                                         compute='_compute_stat_buttons_from_advance',
                                         help="Invoices whose journal items have been reconciled with these payments.")
    advanced_outgoing_count = fields.Integer(string="# Advance O/P",
                                          compute="_compute_stat_buttons_from_advance")

    @api.depends('property_account_payable_advance_id', 'property_account_receivable_advance_id')
    def _compute_stat_buttons_from_advance(self):
        ''' Retrieve the invoices reconciled to the payments through the reconciliation (account.partial.reconcile). '''
        stored_payments_inbound = self.env['account.payment'].search([('stored_advance_residual', '>', 0),('payment_type', '=', 'inbound'),
                                                              ('partner_id', '=', self.id),('is_advance_payment', '=', True)])
        stored_payments_outbound = self.env['account.payment'].search(
            [('stored_advance_residual', '>', 0), ('payment_type', '=', 'outbound'),
            ('partner_id', '=', self.id),('is_advance_payment', '=', True)])
        if not stored_payments_inbound and not stored_payments_outbound:
            self.advanced_incoming_ids = False
            self.advanced_incoming_count = 0
            self.advanced_outgoing_ids = False
            self.advanced_outgoing_count = 0
            return
        if stored_payments_inbound:
            self.advanced_incoming_ids += self.env['account.payment'].browse(stored_payments_inbound.ids)
            self.advanced_incoming_count = len(stored_payments_inbound.ids)
        else:
            self.advanced_incoming_ids = False
            self.advanced_incoming_count = 0
        if stored_payments_outbound:
            self.advanced_outgoing_ids += self.env['account.payment'].browse(stored_payments_outbound.ids)
            self.advanced_outgoing_count = len(stored_payments_outbound.ids)
        else:
            self.advanced_outgoing_ids = False
            self.advanced_outgoing_count = 0


    def button_open_outbound_advanced(self):
        ''' Redirect the user to the bill(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Advance outgoing payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(self.advanced_outgoing_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.advanced_outgoing_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.advanced_outgoing_ids.ids)],
            })
        return action

    def button_open_inbound_advanced(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Advance incoming payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(self.advanced_incoming_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.advanced_incoming_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.advanced_incoming_ids.ids)],
            })
        return action
