# -*- coding: utf-8 -*-
#  Copyright (c) 2018 - Indexa SRL. (<https://www.indexa.do/>)
#  See LICENSE file for full copyright and licensing details.

import json
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_invoice_currency_rate(self, invoice, commission_currency_rate):

        currency_id = invoice.currency_id
        date = invoice.date_invoice if commission_currency_rate == 'invoice' else fields.Date.context_today(self)
        rate = self.env['res.currency.rate'].search([('currency_id', '=', currency_id.id),
                                                     ('name', '=', date)], limit=1)

        return rate.rate if rate else 1

    def _get_invoice_line_commission(self, invoice_line, commission_base, commission_schema, invoice, payment_amount,
                                     commission_currency_rate):

        product_id = invoice_line.product_id
        price = (
            invoice_line.price_unit
            if invoice.currency_id.id == invoice.company_id.currency_id.id
            else invoice_line.price_unit / self._get_invoice_currency_rate(
                invoice, commission_currency_rate
            )
        )
        quantity = invoice_line.quantity
        subtotal = (price * quantity) - (
            ((price * quantity) * invoice_line.discount / 100) if invoice_line.discount else 0
        )

        percentage = product_id.percentage if product_id.percentage != 0 else product_id.categ_id.percentage \
            if product_id.categ_id.commission else 0
        fixed_amount = (
            product_id.fixed_amount
            if product_id.fixed_amount != 0
            else product_id.categ_id.fixed_amount if product_id.categ_id.commission else 0
        ) / self._get_invoice_currency_rate(
            invoice, commission_currency_rate
        )
        currency = invoice.currency_id
        taxes = invoice_line.invoice_line_tax_ids.compute_all(price, currency, quantity, product=product_id,
                                                              partner=invoice.partner_id)

        if commission_base == 'gross':

            subtotal_due = invoice.residual - (invoice.amount_total - invoice.amount_untaxed)
            if subtotal_due > 0 or payment_amount == invoice.amount_total:

                if commission_schema == 'liquidate':
                    payment_amount = invoice.amount_untaxed
                elif payment_amount > subtotal_due:
                    payment_amount = subtotal_due

                commission = round(((subtotal / invoice.amount_untaxed) * payment_amount) *
                                   (percentage / 100 if percentage > 0 else 0), 4) + fixed_amount

                return commission

            else:

                # Return zero because the total of untaxed amount
                # commission was already posted
                return 0

        elif commission_base == 'net':

            tax_incl = taxes['total_included'] if taxes else subtotal
            if commission_schema == 'liquidate':
                payment_amount = invoice.amount_total

            commission = round(((tax_incl / invoice.amount_total) * payment_amount) *
                               (percentage / 100 if percentage > 0 else 0), 4) + fixed_amount

            return commission

        else:
            raise ValidationError(_('Error. Unknown Commission Base. Check your Commission Settings.'))

    def _get_invoice_commission(self, invoice, payment_amount, commission_schema, commission_currency_rate):

        ICP = self.env['ir.config_parameter'].sudo()
        commission_base = ICP.get_param('account_sale_commission.commission_base')
        gilc = self._get_invoice_line_commission
        result = {}

        for line in invoice.invoice_line_ids:
            if line.product_id and line.product_id.commission_ok:
                if line.product_id.id not in result:
                    result.update({
                        line.product_id.id: gilc(line, commission_base, commission_schema, invoice, payment_amount,
                                                 commission_currency_rate)
                    })
                else:
                    result[line.product_id.id] += gilc(line, commission_base, commission_schema, invoice,
                                                       payment_amount, commission_currency_rate)

        return result

    def _get_commission_beneficiary(self, invoice, beneficiary):

        current_user_partner = self.env.user.partner_id

        if beneficiary == 'invoice':
            return invoice.user_id.partner_id or current_user_partner
        elif beneficiary == 'partner':
            return invoice.partner_id.user_id.partner_id or current_user_partner
        else:
            return current_user_partner

    def _create_commission_entry(self):
        ICP = self.env['ir.config_parameter'].sudo()
        commission_schema = ICP.get_param('account_sale_commission.commission_schema')
        commission_beneficiary = ICP.get_param('account_sale_commission.commission_beneficiary')
        commission_currency_rate = ICP.get_param('account_sale_commission.commission_currency_rate')
        move_date = ICP.get_param('account_sale_commission.move_date')

        date_now = fields.Datetime.now()

        # Commission based on each invoice payment
        if commission_schema == 'pays':
            # Validates if current payment journal can pay commission
            if self.journal_id.commission:

                invoice_ids = self.env['account.invoice'].browse(self._context.get('active_ids'))

                for invoice in invoice_ids:

                    outstanding_credit = self._context.get('outstanding_credit', 0)

                    # amount = outstanding_credit when payment was applied from invoice
                    # outstanding_credit widget
                    payment_amount = outstanding_credit if outstanding_credit else self.amount

                    partner_id = self._get_commission_beneficiary(invoice, commission_beneficiary)
                    journal_id = invoice.company_id.commission_journal_id
                    debit_acc = invoice.company_id.commission_debit_account
                    credit_acc = invoice.company_id.commission_credit_account

                    # If any of the fields above is false, the commission journal entry is not performed
                    if not any([journal_id is False, debit_acc is False, credit_acc is False]):
                        amount = sum([v for k, v in dict(
                            self._get_invoice_commission(invoice, payment_amount, commission_schema,
                                                         commission_currency_rate)).items()])

                        move = self.env['account.move'].sudo().create(
                            {'date': date_now if move_date == 'assignment_date' else self.payment_date,
                             'journal_id': journal_id.id,
                             'line_ids': [[0, 0,
                                           {'account_id': credit_acc.id,
                                            'credit': amount if invoice.type == 'out_invoice' else 0,
                                            'debit': 0 if invoice.type == 'out_invoice' else amount,
                                            'name': _('Invoice %s Sales Commission' % invoice.number),
                                            'partner_id': partner_id.id}],
                                          [0, 0,
                                           {'account_id': debit_acc.id,
                                            'credit': 0 if invoice.type == 'out_invoice' else amount,
                                            'debit': amount if invoice.type == 'out_invoice' else 0,
                                            'name': _('Invoice %s Sales Commission' % invoice.number),
                                            'partner_id': partner_id.id}]],
                             'ref': _('Invoice %s Sales Commission' % invoice.number)})

                        move.sudo().post()

        # Commission based on invoice liquidation
        elif commission_schema == 'liquidate':
            # Validates if current payment journal can pay commission
            if self.journal_id.commission:

                invoice_ids = self.env['account.invoice'].browse(self._context.get('active_ids'))

                for invoice in invoice_ids:

                    outstanding_credit = self._context.get('outstanding_credit', 0)
                    # amount = outstanding_credit when payment was applied from invoice
                    # outstanding_credit widget
                    amount = outstanding_credit if outstanding_credit else self.amount

                    if amount >= invoice.residual:

                        partner_id = self._get_commission_beneficiary(invoice, commission_beneficiary)
                        journal_id = invoice.company_id.commission_journal_id
                        debit_acc = invoice.company_id.commission_debit_account
                        credit_acc = invoice.company_id.commission_credit_account

                        # If any of the fields above is false, the commission journal entry is not performed
                        if not any([journal_id is False, debit_acc is False, credit_acc is False]):
                            amount = sum([v for k, v in dict(
                                self._get_invoice_commission(invoice, invoice.amount_total,
                                                             commission_schema, commission_currency_rate)).items()])

                            move = self.env['account.move'].sudo().create(
                                {'date': date_now if move_date == 'assignment_date' else self.payment_date,
                                 'journal_id': journal_id.id,
                                 'line_ids': [[0, 0,
                                               {'account_id': credit_acc.id,
                                                'credit': amount if invoice.type == 'out_invoice' else 0,
                                                'debit': 0 if invoice.type == 'out_invoice' else amount,
                                                'name': _('Invoice %s Sales Commission' % invoice.number),
                                                'partner_id': partner_id.id}],
                                              [0, 0,
                                               {'account_id': debit_acc.id,
                                                'credit': 0 if invoice.type == 'out_invoice' else amount,
                                                'debit': amount if invoice.type == 'out_invoice' else 0,
                                                'name': _('Invoice %s Sales Commission' % invoice.number),
                                                'partner_id': partner_id.id}]],
                                 'ref': _('Invoice %s Sales Commission' % invoice.number)})

                            move.sudo().post()

            pass

        else:
            raise ValidationError(_('Error. Unknown Commission Schema. Check your Commission Settings.'))

    def post(self):

        for payment in self:
            payment._create_commission_entry()

        return super(AccountPayment, self).post()

    def _get_outstanding_amount(self):
        """ Return payment outstanding credit amount """

        if self.invoice_ids:
            amount = 0
            for invoice in self.invoice_ids:
                for p in invoice._get_invoice_payment_widget():
                    if p.get('account_payment_id', False) == self.id:
                        amount += p['amount']
            return self.amount - amount

        else:
            # If payment hasn't been applied to any invoice,
            # returns payment total amount
            return self.amount


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    commission = fields.Boolean('Generate commission from payments',
                                help="Check this field if payments with this journal creates commission entries "
                                     "for invoices Salesperson")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _get_invoice_payment_widget(self):
        j = json.loads(self.payments_widget)
        return j['content'] if j else []

    def assign_outstanding_credit(self, credit_aml_id):
        self.ensure_one()
        credit_aml = self.env['account.move.line'].browse(credit_aml_id)
        if credit_aml.payment_id:
            payment_id = credit_aml.payment_id
            outstanding_amount = payment_id._get_outstanding_amount()
            payment_id.with_context(
                outstanding_credit=outstanding_amount,
                active_ids=[self.id]
            )._create_commission_entry()
        return super(AccountInvoice, self).assign_outstanding_credit(credit_aml_id)
