# -*- coding: utf-8 -*-
# (C) 2018 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPaymentRecovery(models.Model):
    _name = 'account.payment.recovery'
    _description = 'Advance payment recovery'
    _rec_name = 'payment_id'

    payment_id = fields.Many2one(
        'account.payment', 'Advance payment', ondelete='cascade',
        domain=[('is_advance_payment', '=', True)])
    invoice_id = fields.Many2one(
        'account.move', 'Invoice', required=True)
    amount = fields.Monetary(
        'Recovered amount', required=True)
    company_id = fields.Many2one(
        related='invoice_id.company_id')
    currency_id = fields.Many2one(
        related='invoice_id.currency_id')
    move_id = fields.Many2one(
        'account.move', 'Journal entry')
    # to_journal_id = fields.Many2one('account.journal', related='payment_id.to_journal_id')


    @api.constrains('payment_id', 'amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(
                    _('You cannot recover a negative amount.'))
            if rec.payment_id.stored_advance_residual < 0:
                raise ValidationError(
                    _('%s.', rec.payment_id.stored_advance_residual))

    def post(self):
        for recovery in self:
            move_vals = recovery._get_move_vals()
            line_vals = []
            move_vals['move_type'] = 'entry'
            for type_ in ('counterpart', 'advance'):
                vals = getattr(recovery, '_get_%s_move_line_vals' % type_)()
                if 'credit' in vals and 'amount_currency' in vals:
                    if vals['credit'] > 0:
                        amount_currency_sign = abs(vals['amount_currency']) * -1
                        vals['amount_currency'] = amount_currency_sign

                line_vals.append((0, 0, vals))


            move_vals['line_ids'] = line_vals




            # raise UserError(_("%s",move_vals ))


            recovery.move_id = self.env['account.move'].create(move_vals)

            recovery.move_id._post(soft=True)


            moves_to_reconcile = recovery._get_moves_to_reconcile()

            move_lines = moves_to_reconcile.mapped('line_ids')

            for account in move_lines.mapped('account_id'). \
                    filtered('reconcile'):
                move_lines.filtered(
                    lambda line: line.account_id == account and
                    not line.full_reconcile_id). \
                    reconcile()

            # raise UserError(_("%s", recovery.payment_id))
            recovery.invoice_id.payment_id = recovery.payment_id

            recovery.payment_id.stored_advance_residual -= recovery.amount

        return True

    def _get_moves_to_reconcile(self):
        self.ensure_one()
        return self.move_id | self.invoice_id | \
            self.payment_id.move_id.line_ids.mapped('move_id')

    def _get_move_vals(self):
        self.ensure_one()
        date = self.invoice_id.invoice_date
        payment_journal = self.payment_id.journal_id
        # if payment_journal.recovery_sequence_id:
        #     recovery_sequence = payment_journal.recovery_sequence_id
        # else:
        #      recovery_sequence = payment_journal.sequence_id   
        return {
            'journal_id': payment_journal.id,
            'date': date,
            'ref': self.payment_id.ref or '',
            'currency_id': self.payment_id.currency_id.id
        }

    def _get_shared_move_line_vals(self):
        self.ensure_one()
        return {
            'partner_id': self.invoice_id.partner_id.id,
            # 'move_id': self.invoice_id.id,
            'payment_id': self.payment_id.id,
        }

    def _get_counterpart_move_line_vals(self):
        vals = self._get_shared_move_line_vals()
        amount = self.amount

        from_currency = self.payment_id.currency_id.with_context(
            date=self.invoice_id.invoice_date)
        to_currency = self.company_id.currency_id

        if from_currency != to_currency:
            amount = from_currency.compute(amount, to_currency)

        if self.payment_id.payment_type == 'inbound':
            vals['credit'] = amount
            vals['debit'] = 0.0
        else:
            vals['debit'] = amount
            vals['credit'] = 0.0

        # raise UserError(_("%s", vals))
        
        if vals['debit'] > 0:
            vals['credit'] = 0.0

        if vals['credit'] > 0:
            vals['debit'] = 0.0


        if from_currency != to_currency:
            vals['currency_id'] = self.payment_id.currency_id.id
            vals['amount_currency'] = self.amount

        partner = self.invoice_id.partner_id

        if self.payment_id.payment_type == 'inbound':
            vals['account_id'] = partner.property_account_receivable_id.id
        else:
            vals['account_id'] = partner.property_account_payable_id.id


        return vals

    def _get_advance_move_line_vals(self):
        vals = self._get_counterpart_move_line_vals()
        vals['debit'], vals['credit'] = \
            vals.get('credit', 0.0), vals.get('debit', 0.0)
        partner = self.invoice_id.partner_id

        if self.payment_id.payment_type == 'inbound':
            if not partner.property_account_receivable_advance_id:
                raise UserError(
                    _('Please indicate an account advance receivable '
                        'on this customer'))
            vals['account_id'] = \
                partner.property_account_receivable_advance_id.id
        elif self.payment_id.payment_type == 'outbound':
            if not partner.property_account_payable_advance_id:
                raise UserError(
                    _('Please indicate an account advance payable '
                        'on this supplier'))
            vals['account_id'] = \
                partner.property_account_payable_advance_id.id
        return vals
