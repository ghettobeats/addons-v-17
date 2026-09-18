from odoo import _, api, fields, models
from odoo.exceptions import UserError
import re
from math import copysign
import logging

from odoo.addons.account.models.account_payment_method import AccountPaymentMethod as OriginalAccountPaymentMethod

_logger = logging.getLogger(__name__)

@api.model_create_multi
def create(self, vals_list):
    payment_methods = super(OriginalAccountPaymentMethod,self).create(vals_list)
    methods_info = self._get_payment_method_information()
    for method in payment_methods:
        information = methods_info.get(method.code)

        if information:
            if information.get('mode') == 'multi':
                method_domain = method._get_payment_method_domain()

                journals = self.env['account.journal'].search(method_domain)

                self.env['account.payment.method.line'].create([{
                    'name': method.name,
                    'payment_method_id': method.id,
                    'journal_id': journal.id
                } for journal in journals])
    return payment_methods


OriginalAccountPaymentMethod.create = create


class AccountReconcileModelLine(models.Model):
    _inherit = 'account.payment.method'

    def _get_l10n_do_payment_form(self):
        """ Return the list of payment forms allowed by DGII. """
        return [
            ("cash", _("Cash")),
            ("bank", _("Check / Transfer")),
            ("card", _("Credit Card")),
            ("credit", _("Credit")),
            ("swap", _("Swap")),
            ("bond", _("Bonds or Gift Certificate")),
            ("others", _("Other Sale Type")),
        ]

    l10n_do_payment_form = fields.Selection(
        selection="_get_l10n_do_payment_form", string="Payment Form",
    )





class AccountReconcileModelLine(models.Model):
    _inherit = 'account.reconcile.model'

    # def _get_write_off_move_lines_dict(self, st_line, residual_balance):
    #     ''' Get move.lines dict (to be passed to the create()) corresponding to the reconciliation model's write-off lines.
    #     :param st_line:             An account.bank.statement.line record.(possibly empty, if performing manual reconciliation)
    #     :param residual_balance:    The residual balance of the statement line.
    #     :return: A list of dict representing move.lines to be created corresponding to the write-off lines.
    #     '''
    #     self.ensure_one()
    #
    #     if self.rule_type == 'invoice_matching' and (not self.match_total_amount or (self.match_total_amount_param == 100)):
    #         return []
    #
    #     lines_vals_list = []
    #
    #     for line in self.line_ids:
    #         if not line.account_id or st_line.company_currency_id.is_zero(residual_balance):
    #             return []
    #
    #         if line.amount_type == 'percentage':
    #             balance = residual_balance * (line.amount / 100.0)
    #         elif line.amount_type == "regex":
    #             match = re.search(line.amount_string, st_line.payment_ref)
    #             if match:
    #                 sign = 1 if residual_balance > 0.0 else -1
    #                 extracted_balance = float(re.sub(r'\D' + self.decimal_separator, '', match.group(1)).replace(self.decimal_separator, '.'))
    #                 balance = copysign(extracted_balance * sign, residual_balance)
    #             else:
    #                 balance = 0
    #         else:
    #             balance = line.amount * (1 if residual_balance > 0.0 else -1)
    #
    #         writeoff_line = {
    #             'name': line.label or st_line.payment_ref,
    #             'balance': balance,
    #             'debit': balance > 0 and balance or 0,
    #             'credit': balance < 0 and -balance or 0,
    #             'account_id': line.account_id.id,
    #             'currency_id': st_line.currency_id.id,
    #             'amount_currency': st_line.amount,
    #             'analytic_account_id': line.analytic_account_id.id,
    #             'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
    #             'reconcile_model_id': self.id,
    #         }
    #         lines_vals_list.append(writeoff_line)
    #
    #         residual_balance -= balance
    #
    #         if line.tax_ids:
    #             writeoff_line['tax_ids'] = [(6, None, line.tax_ids.ids)]
    #             tax = line.tax_ids
    #             # Multiple taxes with force_tax_included results in wrong computation, so we
    #             # only allow to set the force_tax_included field if we have one tax selected
    #             if line.force_tax_included:
    #                 tax = tax[0].with_context(force_price_include=True)
    #             tax_vals_list = self._get_taxes_move_lines_dict(tax, writeoff_line)
    #             lines_vals_list += tax_vals_list
    #             if not line.force_tax_included:
    #                 for tax_line in tax_vals_list:
    #                     residual_balance -= tax_line['balance']
    #
    #     return lines_vals_list

class AccountPaymentInvoices(models.Model):
    _name = 'account.payment.invoice'


    subtotal = fields.Monetary(string="Subtotal", store=True, compute="compute_subtotal",currency_field='currency_id')
    itbis = fields.Monetary(related="invoice_id.invoiced_itbis", string="ITBIS",currency_field='currency_id')
    itbis_withold = fields.Monetary(string="ITBIS retenido", default=0.0, store=True, compute="compute_withold",currency_field='currency_id')
    isr_withold = fields.Monetary(string="ISR retenido", default=0.0, store=True, compute="compute_withold",currency_field='currency_id')
    tc_withold = fields.Monetary(string="TC Comision retenida", default=0.0, store=True, compute="compute_withold",
                                  currency_field='currency_id')
    withold_method_line = fields.Selection(related='payment_id.withold_method', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_id = fields.Many2one('account.payment', string='Payment')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    origin = fields.Char(related='invoice_id.invoice_origin')
    date_invoice = fields.Date(related='invoice_id.invoice_date')
    date_due = fields.Date(related='invoice_id.invoice_date_due')
    payment_state = fields.Selection(related='payment_id.state', store=True)
    reconcile_amount = fields.Monetary(string='Reconcile Amount')
    amount_total = fields.Monetary(related="invoice_id.amount_total")
    residual = fields.Monetary(related="invoice_id.amount_residual")
    add_invoice = fields.Boolean(string='Select',default=False, store=True)
    compute_manual_retention_field = fields.Boolean(string='Computar retencion manualmente?', default=False, store=True, compute="compute_manual_retention")
    itbis_withold_manual = fields.Monetary(string="ITBIS retenido manual", default=0.0,
                                    currency_field='currency_id')
    isr_withold_manual = fields.Monetary(string="ISR retenido manual", default=0.0,
                                  currency_field='currency_id')
    tc_withold_manual = fields.Monetary(string="TC Comision retenida manual", default=0.0,
                                 currency_field='currency_id')


    @api.depends('payment_id.manual_retentions')
    def compute_manual_retention(self):
        for line in self:
            if line.payment_id.manual_retentions == True:
                line.compute_manual_retention_field = True
            else:
                line.compute_manual_retention_field = False


    @api.depends('itbis','amount_total')
    def compute_subtotal(self):
        for invoices in self:
            if invoices.itbis > 0:
                invoices.subtotal = invoices.amount_total - invoices.itbis
            else:
                invoices.subtotal = invoices.amount_total

    @api.depends('add_invoice', 'reconcile_amount','payment_id.withold_itbis_select','payment_id.withold_isr_select','payment_id.withold_tc_select','itbis_withold_manual',
                 'isr_withold_manual', 'tc_withold_manual','compute_manual_retention_field')
    def compute_withold(self):
        for invoices in self:
            if invoices.compute_manual_retention_field == False:
                if invoices.payment_id.withold_itbis_select and invoices.add_invoice == True \
                    and invoices.payment_id.withold_itbis_select.sale_itbis_retention_type != '01' and invoices.payment_id.withold_itbis_select.amount_type != 'fixed':
                    if invoices.payment_id.withold_itbis_select.amount == - 5.4000:
                        invoices.itbis_withold = (0.30 * invoices.itbis)
                    elif invoices.payment_id.withold_itbis_select.amount == - 13.5000:
                        invoices.itbis_withold = (0.75 * invoices.itbis)
                    elif invoices.payment_id.withold_itbis_select.amount == - 18.0:
                        invoices.itbis_withold = (1 * invoices.itbis)
                    else:
                        invoices.itbis_withold = - ((invoices.payment_id.withold_itbis_select.amount / 100) * invoices.itbis)
                elif invoices.payment_id.withold_itbis_select.amount > 0 and invoices.payment_id.withold_itbis_select.amount_type == 'fixed':
                    invoices.itbis_withold = invoices.payment_id.withold_itbis_select.amount
                elif invoices.payment_id.withold_itbis_select and invoices.add_invoice == True \
                    and invoices.payment_id.withold_itbis_select.sale_itbis_retention_type == '01'  and invoices.payment_id.withold_itbis_select.amount_type != 'fixed':
                        invoices.itbis_withold = - ((invoices.payment_id.withold_itbis_select.amount / 100) * (invoices.itbis + invoices.subtotal))
                else:
                    invoices.itbis_withold = 0.0
            if invoices.compute_manual_retention_field == True:
                invoices.itbis_withold = invoices.itbis_withold_manual
                invoices.isr_withold = invoices.isr_withold_manual
                invoices.tc_withold = invoices.tc_withold_manual

            for invoices in self:
                if invoices.compute_manual_retention_field == False:
                    if invoices.payment_id.withold_isr_select and invoices.add_invoice == True:
                        invoices.isr_withold = - ((invoices.payment_id.withold_isr_select.amount / 100) * invoices.subtotal)
                    else:
                        invoices.isr_withold = 0.0
                    if invoices.payment_id.withold_tc_select and invoices.add_invoice == True:
                        invoices.tc_withold = - ((invoices.payment_id.withold_tc_select.amount / 100) * (invoices.itbis + invoices.subtotal))
                    else:
                        invoices.tc_withold = 0.0
                if invoices.compute_manual_retention_field == True:
                    invoices.itbis_withold = invoices.itbis_withold_manual
                    invoices.isr_withold = invoices.isr_withold_manual
                    invoices.tc_withold = invoices.tc_withold_manual


    @api.onchange('add_invoice','invoice_id','itbis_withold_manual',
                 'isr_withold_manual', 'tc_withold_manual','compute_manual_retention_field')
    def add_invoice_toggle(self):
        for invoices in self:
            if invoices.add_invoice == True:
                invoices.reconcile_amount = invoices.residual - invoices.isr_withold - invoices.itbis_withold - invoices.tc_withold
            elif invoices.add_invoice == False:
                invoices.reconcile_amount = 0.0
            else:
                return


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_id = fields.Many2one('account.move', string='Invoice')

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    amount_in_journal_currency = fields.Monetary('Monto en moneda de diario', store=True, compute="_compute_currency_rate",currency_field='journal_currency_id')
    payment_rate = fields.Float('Tasa de cambio en pago', store=True)
    different_currencies = fields.Boolean('Monedas diferentes en pago', compute='moneda_diferente')
    tasa_manual = fields.Boolean('Tasa manual?')
    journal_currency_id = fields.Many2one(related='journal_id.currency_id')
    different_currencies_2 = fields.Boolean('Monedas diferentes en pago', compute='moneda_diferente_2')

    @api.onchange('different_currencies', 'journal_id')
    def moneda_diferente_2(self):
        for rec in self:
            if rec.journal_currency_id:
                if (rec.currency_id == rec.journal_currency_id and rec.journal_currency_id != rec.company_id.currency_id) \
                        and rec.different_currencies == False:
                    rec.different_currencies_2 = True
                else:
                    rec.different_currencies_2 = False
            else:
                rec.different_currencies_2 = False

    @api.onchange('is_internal_transfer', 'currency_id', 'tasa_manual')
    def bloqueo_transferencia_interna_moneda(self):
        for rec in self:
            if rec.is_internal_transfer and rec.internal_transfer_type == 'j_to_j' and rec.journal_currency_id != rec.currency_id:
                raise UserError(
                    _("Una transferencia interna entre diarios (o entre bancos) no puede tener una moneda diferente a la del banco seleccionado. "
                      "Los montos a transferir se crearan segun los montos colocados en las casillas de 'Importe' y 'Monto a recibir', asentandose asi "
                      "en libro el valor correcto."))
            if rec.is_internal_transfer and rec.internal_transfer_type == 'j_to_j' and rec.tasa_manual == True:
                raise UserError(
                    _("Una transferencia interna entre diarios (o entre bancos) no puede tener una moneda diferente a la del banco seleccionado. "
                      "Los montos a transferir se crearan segun los montos colocados en las casillas de 'Importe' y 'Monto a recibir', asentandose asi "
                      "en libro el valor correcto."))

    # APLICAR BYPASS EN INSTALACION
    @api.onchange('different_currencies', 'amount', 'currency_id', 'payment_rate', 'journal_id')
    def _compute_currency_rate(self):
        for rec in self:
            rec.amount_in_journal_currency = 0.0
            if rec.state == 'draft':
                if rec.different_currencies == True and rec.currency_id and rec.journal_currency_id and rec.tasa_manual == False:
                    if rec.journal_currency_id == rec.company_id.currency_id:
                        rec.payment_rate = rec.currency_id._get_conversion_rate(rec.currency_id,
                                                                                rec.journal_currency_id,
                                                                                rec.company_id,
                                                                                rec.date or fields.Date.context_today(
                                                                                    rec))
                        rec.amount_in_journal_currency = rec.payment_rate * rec.amount
                    elif rec.journal_currency_id != rec.company_id.currency_id:
                        rec.payment_rate = 1 / rec.currency_id._get_conversion_rate(rec.currency_id,
                                                                                    rec.journal_currency_id,
                                                                                    rec.company_id,
                                                                                    rec.date or fields.Date.context_today(
                                                                                        rec))
                        rec.amount_in_journal_currency = rec.amount / rec.payment_rate
                elif rec.different_currencies == True and rec.currency_id and rec.journal_currency_id and rec.tasa_manual == True:
                    if rec.journal_currency_id == rec.company_id.currency_id:
                        rec.amount_in_journal_currency = rec.payment_rate * rec.amount
                    elif rec.journal_currency_id != rec.company_id.currency_id:
                        rec.amount_in_journal_currency = rec.amount / rec.payment_rate

                if rec.different_currencies_2 == True and rec.currency_id and rec.journal_currency_id and rec.tasa_manual == False:
                    if rec.journal_currency_id != rec.company_id.currency_id:
                        rec.payment_rate = 1 / rec.currency_id._get_conversion_rate(rec.company_id.currency_id,
                                                                                    rec.currency_id,
                                                                                    rec.company_id,
                                                                                    rec.date or fields.Date.context_today(
                                                                                        rec))

    @api.onchange('journal_id', 'currency_id')
    def moneda_diferente(self):
        for rec in self:
            if rec.journal_currency_id:
                if rec.currency_id != rec.journal_id.currency_id and (rec.currency_id == rec.company_id.currency_id or \
                                                                      rec.journal_currency_id == rec.company_id.currency_id):
                    rec.different_currencies = True
                else:
                    rec.different_currencies = False
            else:
                rec.different_currencies = False

    manual_retentions = fields.Boolean(string='Modificar retenciones manualmente?',
                                       default=False, store=True)

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash','general'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()


                # if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, the journal entry must always contains:\n"
                #         "- one journal item involving the outstanding payment/receipts account.\n"
                #         "- one journal item involving a receivable/payable account.\n"
                #         "- optional journal items, all sharing the same account.\n\n"
                #     ) % move.display_name)

                # if writeoff_lines and len(writeoff_lines.account_id) != 1:
                #     raise UserError(_(
                #         "The journal entry %s reached an invalid state relative to its payment.\n"
                #         "To be consistent, all the write-off journal items must share the same account."
                #     ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id and all_lines[0].account_id.user_type_id.type in ('bank', 'cash') for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                # if counterpart_lines:
                #     for counterpart_liness in counterpart_lines:
                #         if counterpart_liness.account_id.user_type_id.type == 'receivable' and counterpart_liness.account_id != pay.partner_id.property_account_receivable_advance_id:
                #             partner_type = 'customer'
                #         else:
                #             partner_type = 'supplier'
                # else:
                partner_type = pay.partner_type

                amount_currency_liq = 0.0
                amount_debit_credit = 0.0
                for liquidity in liquidity_lines:
                    amount_currency_liq += liquidity.amount_currency
                    amount_debit_credit += liquidity.debit - liquidity.credit

                liquidity_amount = amount_currency_liq

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })

                if pay.is_internal_transfer and writeoff_lines:
                    writeoff_lines[0].partner_id = pay.partner_id

                if pay.journal_currency_id == pay.currency_id:
                    payment_vals_to_write.update({
                        'amount': abs(liquidity_amount),
                        'payment_type': 'inbound' if liquidity_amount > 0.0 else pay.payment_type,
                        'partner_type': partner_type,
                        'currency_id': liquidity_lines.currency_id.id,
                        'destination_account_id': counterpart_lines[0].account_id.id if counterpart_lines else writeoff_lines[0].account_id.id,
                        'partner_id': (liquidity_lines.partner_id.id if counterpart_lines[0].partner_id.id == liquidity_lines.partner_id.id \
                            else counterpart_lines[0].partner_id.id) if liquidity_lines and counterpart_lines else writeoff_lines[0].partner_id.id,
                    })
                elif pay.journal_currency_id != pay.currency_id and pay.journal_currency_id == pay.company_id.currency_id:
                    payment_vals_to_write.update({
                        'amount': abs(liquidity_amount),
                        'payment_type': 'inbound' if liquidity_amount > 0.0 else pay.payment_type,
                        'partner_type': partner_type,
                        'currency_id': liquidity_lines.currency_id.id,
                        'destination_account_id': counterpart_lines[0].account_id.id if counterpart_lines else
                        writeoff_lines[0].account_id.id,
                        'partner_id': (liquidity_lines.partner_id.id if counterpart_lines[
                                                                            0].partner_id.id == liquidity_lines.partner_id.id \
                                           else counterpart_lines[
                            0].partner_id.id) if liquidity_lines and counterpart_lines else writeoff_lines[
                            0].partner_id.id,
                    })
                elif pay.journal_currency_id != pay.currency_id and pay.journal_currency_id != pay.company_id.currency_id:
                    payment_vals_to_write.update({
                        'amount': abs(amount_debit_credit) if pay.currency_id == pay.company_id.currency_id else abs(liquidity.amount_currency),
                        'payment_type': 'inbound' if amount_debit_credit > 0.0 else 'outbound',
                        'partner_type': partner_type,
                        'destination_account_id': counterpart_lines[0].account_id.id if counterpart_lines else
                        writeoff_lines[0].account_id.id,
                        'partner_id': (liquidity_lines.partner_id.id if counterpart_lines[
                                                                            0].partner_id.id == liquidity_lines.partner_id.id \
                                           else counterpart_lines[
                            0].partner_id.id) if liquidity_lines and counterpart_lines else writeoff_lines[
                            0].partner_id.id,
                    })


            # raise UserError(_("%s", move_vals_to_write))
            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    # @api.onchange('journal_id')
    # def internal_transfer_test(self):
    #     for pay in self:
    #         pay.is_internal_transfer = True
    #         pay.amount = 500
    #         pay.to_journal_id = self.env['account.journal'].search([('id', '=', 27)])
    #         pay.amount_to_journal = 500 * 60.00

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        if self.is_internal_transfer and self.internal_transfer_type == 'j_to_j' and self.parent_internal_transfer == True:
            default.update(
                parent_internal_transfer=False,
                child_internal_transfer=False)
        if self.is_internal_transfer and self.internal_transfer_type == 'j_to_j' and self.child_internal_transfer == True:
            raise UserError(_("No puede copiar una transferencia desde la hija, favor vaya a la padre y dupliquela."))

        return super(AccountPayment, self).copy(default)

    @api.model
    def create(self, vals_list):
        # self.change_menu_names()
        res = super(AccountPayment, self).create(vals_list)
        # raise UserError(_("%s", vals_list))
        related_transfer = self.env['account.payment']
        # if 'payment_invoice_ids' not in vals_list and 'withold_method' in vals_list:
        #     if vals_list['withold_method'] in ('itbis', 'isr','itbis_isr'):
        #         raise UserError(_("No puede registrar un pago con retenciones de ITBIS y/o ISR sin afectar una factura. "
        #                           "Los unicos pagos que puede registrar con retenciones y sin factura son los pagos recibidos"
        #                           " de tarjetas de credito para aplicar la comision y la norma 08-04 segun la politica de la empresa."))

        if 'is_internal_transfer' in vals_list and 'to_journal_id' in vals_list and 'amount_to_journal' in vals_list and 'internal_transfer_type' in vals_list:
            if vals_list['internal_transfer_type'] == 'j_to_j' and vals_list['is_internal_transfer'] == True:
                journal = self.env['account.journal'].search([('id','=',vals_list['to_journal_id'])])

                # raise UserError(_("%s, %s", ('parent_internal_transfer', 'child_internal_transfer') not in vals_list,
                #                   ('parent_internal_transfer', 'child_internal_transfer') not in vals_list))

                if vals_list['amount_to_journal'] == 0.0 or vals_list['amount_to_journal'] < 0.0:
                    raise UserError(
                        _("No puede registrar una transferencia entre diarios si el monto a transferir en el diario receptor "
                          "es igual o inferior a cero."))

                if journal.type not in ('bank','cash'):
                    raise UserError(
                        _("No puede registrar una transferencia entre diarios si los mismos no son de efectivo o de banco. Para "
                          "realizar una transferencia de un diario a una cuenta favor seleccionar el metodo correcto."))


                if 'parent_internal_transfer' in vals_list and 'child_internal_transfer' in vals_list:

                    if vals_list['child_internal_transfer'] == False and vals_list['parent_internal_transfer'] == False:

                        # raise UserError(_("%s", vals_list))

                        internal_transfer = {
                            'payment_type': 'inbound' if vals_list['payment_type'] == 'outbound' else 'outbound',
                            'journal_id': vals_list['to_journal_id'],
                            'is_internal_transfer': True,
                            'internal_transfer_type': 'j_to_j',
                            'company_id': journal.company_id.id,
                            'currency_id': journal.currency_id.id,
                            'amount': vals_list['amount_to_journal'],
                            'amount_to_journal': vals_list['amount'],
                            'to_journal_id': vals_list['journal_id'],
                            'related_payment_transfer': res.id,
                            'date': vals_list['date'] if 'date' in vals_list else fields.Datetime.today(),
                            'child_internal_transfer': True,

                        }

                        related_transfer.create(internal_transfer)

                if 'child_internal_transfer' in vals_list and 'related_payment_transfer' in vals_list:
                    if vals_list['child_internal_transfer'] == True:
                        payment_related = self.env['account.payment'].search([('id', '=',vals_list['related_payment_transfer'])])
                        payment_related.write({
                            'related_payment_transfer': res.id,
                            'parent_internal_transfer': True,
                        })
                    # raise UserError(_("si"))

        return res

    @api.depends('move_id.name')
    def name_get(self):
        # raise UserError(_("%s", [(payment.id, payment.move_id.name if payment.move_id.name != '/' else _('Pago borrador (* %s)',payment.id) or _('Draft Payment')) for payment in self]))
        return [(payment.id, payment.move_id.name if payment.move_id.name != '/' else _('Pago borrador (* %s)',payment.id) or _('Draft Payment')) for payment in self]

    def unlink(self, child=False):
        for pay in self:
            if pay.is_internal_transfer and pay.related_payment_transfer:
                if pay.parent_internal_transfer:
                    pay.related_payment_transfer.unlink(child=True)
                elif child:
                    return super(AccountPayment, self).unlink()
                else:
                    raise UserError(
                        _("No puede eliminar un pago interno hijo, favor dirigirse a la transferencia padre y borre la transaccion "
                          "desde ahi. Transferencia padre: %s", pay.related_payment_transfer.name))
        return super(AccountPayment, self).unlink()

    def action_draft(self):
        res = super(AccountPayment, self).action_draft()
        for payment in self:
            if payment.related_payment_transfer and payment.parent_internal_transfer:
                payment.related_payment_transfer.action_draft()

        return res

    def write(self, vals, child=False):

        self._synchronize_to_moves(set(vals.keys()), vals)

        # for rec in self:
        #     if 'payment_invoice_ids' not in vals and 'withold_method' in vals:
        #         if vals['withold_method'] in ('itbis', 'isr','itbis_isr'):
        #             raise UserError(_("No puede registrar un pago con retenciones de ITBIS y/o ISR sin afectar una factura. "
        #                               "Los unicos pagos que puede registrar con retenciones y sin factura son los pagos recibidos"
        #                               " de tarjetas de credito para aplicar la comision y la norma 08-04 segun la politica de la empresa."))
        #     elif not rec.payment_invoice_ids and rec.withold_method not in ('default', False):
        #         if rec.withold_method in ('itbis', 'isr', 'itbis_isr'):
        #             raise UserError(
        #                 _("No puede registrar un pago con retenciones de ITBIS y/o ISR sin afectar una factura. "
        #                   "Los unicos pagos que puede registrar con retenciones y sin factura son los pagos recibidos"
        #                   " de tarjetas de credito para aplicar la comision y la norma 08-04 segun la politica de la empresa."))


        for pay in self:
            # raise UserError(_("%s", vals))
            if ('is_internal_transfer') in vals:
                if vals['is_internal_transfer'] == False:
                    raise UserError(
                        _("No puede cambiar una transferencia interna una vez registrada como interna. "
                          "Si desea hacer un cambio de este tipo favor borre (si puede) o cancele y haga una nueva."))

            #if ('currency_id') in vals and child==False:
                # raise UserError(_("%s, %s", vals, pay.currency_id.id))
            #    if pay.currency_id:
            #        if pay.currency_id.id != vals['currency_id']:
            #            raise UserError(
            #                _("No puede cambiar la moneda del pago una vez creado. Favor de borrar (si puede) o cancelar "
            #                  "la misma y rehacer con la moneda correcta."))


            # raise UserError(_("%s, %s", vals,pay.is_internal_transfer))
            if (('amount_to_journal') in vals or ('amount') in vals) and pay.is_internal_transfer and pay.internal_transfer_type == 'j_to_j':

                if pay.journal_id.type not in ('bank','cash'):
                    raise UserError(
                        _("No puede registrar una transferencia entre diarios si los mismos no son de efectivo o de banco. Para "
                          "realizar una transferencia de un diario a una cuenta favor seleccionar el metodo correcto."))

                if pay.parent_internal_transfer and 'amount' in vals and  child == False and not 'amount_to_journal' in vals:
                    pay.related_payment_transfer.write({
                        'amount_to_journal': vals['amount']
                    }, child=True)
                elif pay.parent_internal_transfer and 'amount_to_journal' in vals and child == False and not 'amount' in vals:

                    if vals['amount_to_journal'] == 0.0 or vals['amount_to_journal'] < 0.0:
                        raise UserError(
                            _("No puede registrar una transferencia entre diarios si el monto a transferir en el diario receptor "
                              "es igual o inferior a cero."))

                    pay.related_payment_transfer.write({
                        'amount': vals['amount_to_journal']
                    }, child=True)

                elif pay.parent_internal_transfer and 'amount_to_journal' in vals and 'amount' in vals and child == False:
                    if vals['amount_to_journal'] == 0.0 or vals['amount_to_journal'] < 0.0:
                        raise UserError(
                            _("No puede registrar una transferencia entre diarios si el monto a transferir en el diario receptor "
                              "es igual o inferior a cero."))

                    pay.related_payment_transfer.write({
                        'amount': vals['amount_to_journal'],
                        'amount_to_journal': vals['amount']
                    }, child=True)


                elif child == False and pay.child_internal_transfer:
                    # raise UserError(_("%s, %s", pay.internal_transfer_type, pay.amount_to_journal))
                    raise UserError(
                        _("No puede modificar una transferencia interna hija, "
                          "favor dirigase a la transferencia padre para modificar: %s.",
                          pay.related_payment_transfer.name))


        return super(AccountPayment, self).write(vals)

    @api.depends('is_internal_transfer')
    def _compute_partner_id(self):
        for pay in self:
            if pay.is_internal_transfer and pay.internal_transfer_type == 'j_to_j':
                pay.partner_id = pay.journal_id.company_id.partner_id
            elif pay.partner_id == pay.journal_id.company_id.partner_id and pay.internal_transfer_type == 'j_to_j':
                pay.partner_id = False
            elif pay.internal_transfer_type == 'j_to_a' and pay.investor_id:
                pay.partner_id = pay.investor_id
            else:
                pay.partner_id = pay.partner_id

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the temporary liquidity account.
        - The lines using the counterpart account.
        - The lines being the write-off lines.
        :return: (liquidity_lines, counterpart_lines, writeoff_lines)
        '''
        self.ensure_one()


        liquidity_lines = self.env['account.move.line']
        counterpart_lines = self.env['account.move.line']
        writeoff_lines = self.env['account.move.line']

        for line in self.move_id.line_ids:
            if line.account_id in (self.journal_id.payment_debit_account_id, self.journal_id.payment_credit_account_id,
                                   self.journal_id.default_account_id):
                liquidity_lines += line
            elif (line.account_id.internal_type in ('receivable', 'payable') or line.account_id == self.destination_account_id) and line.account_id not in (
            self.journal_id.payment_debit_account_id, self.journal_id.payment_credit_account_id,
            self.journal_id.default_account_id):
                counterpart_lines += line
                for count in counterpart_lines:
                    if self.partner_id.id != self.investor_id.id and count.partner_id.id != self.partner_id.id:
                        count.partner_id = self.partner_id
            else:
                writeoff_lines += line


        return liquidity_lines, counterpart_lines, writeoff_lines

    internal_transfer_type = fields.Selection([('j_to_j', 'Diario <-> Diario'), ('j_to_a', 'Diario <-> Cuenta')], string='Tipo de transferencia interna', default='j_to_j')
    to_account_id = fields.Many2one('account.account', string="Transferir a/desde cuenta")
    to_journal_id = fields.Many2one('account.journal', string="Transferir a/desde diario", domain=[('type', 'in', ('bank','cash'))])
    currency_to_journal = fields.Many2one(related="to_journal_id.currency_id")
    amount_to_journal = fields.Monetary('Monto a recibir', currency_field="currency_to_journal")
    related_payment_transfer = fields.Many2one('account.payment',string="Transferencia relacionada", copy=False)
    parent_internal_transfer = fields.Boolean(string='Es transferencia padre interna?', copy=False)
    child_internal_transfer = fields.Boolean(string='Es transferencia hija interna?', copy=False)

    @api.model
    def change_menu_names(self):
        if self.env.ref("account.menu_action_account_payments_receivable").name != "Pagos entrantes":
            self.env.ref("account.menu_action_account_payments_receivable").name = "Pagos entrantes"
        if self.env.ref("account.menu_action_account_payments_payable").name != "Pagos salientes":
            self.env.ref("account.menu_action_account_payments_payable").name = "Pagos salientes"
        if self.env.ref("account.menu_finance").name != "Contabilidad":
            self.env.ref("account.menu_finance").name = "Contabilidad"


    @api.onchange('to_account_id')
    def get_balance_caja_chica(self):
        for rec in self:
            if rec.to_account_id.es_caja_chica:
                today = fields.Date.context_today(self)
                query = '''
                                SELECT move.account_id,
                                    (move.debit - move.credit) as balance
                                FROM account_move_line move
                                WHERE move.account_id = %s
                                AND move.date <= %s
                                AND move.parent_state = 'posted';
                            '''
                self.env.cr.execute(query, (rec.to_account_id.id, today))
                late_query_results = self.env.cr.dictfetchall()
                if late_query_results:
                    rec.amount = late_query_results[0]['balance']


    @api.depends('partner_id', 'destination_account_id', 'journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            if payment.internal_transfer_type == 'j_to_a':
                is_partner_ok = True
                is_account_ok = True
                return
            else:
                is_partner_ok = payment.partner_id == payment.journal_id.company_id.partner_id
            is_account_ok = payment.destination_account_id == payment.journal_id.company_id.transfer_account_id
            # raise UserError(_("%s, %s", payment.partner_id, is_account_ok ))
            payment.is_internal_transfer = is_partner_ok and is_account_ok




    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company, readonly=True)

    @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer', 'internal_transfer_type',
                 'to_account_id', 'to_journal_id')
    def _compute_destination_account_id(self):
        self.destination_account_id = False
        for pay in self:
            if pay.is_internal_transfer:
                pay.destination_account_id = pay.journal_id.company_id.transfer_account_id

                if pay.internal_transfer_type == 'j_to_a':
                    pay.destination_account_id = pay.to_account_id

                if pay.internal_transfer_type == 'j_to_j':
                    pay.destination_account_id = pay.journal_id.company_id.transfer_account_id

            elif pay.partner_type == 'customer':
                # Receive money from invoice or send money to refund it.
                if pay.partner_id and not pay.is_advance_payment:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_receivable_id
                elif pay.is_advance_payment:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_receivable_advance_id.id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('user_type_id.name', 'in', ('Non-current Liabilities','Receivable'))
                    ], limit=1)
            elif pay.partner_type == 'supplier':
                # Send money to pay a bill or receive money to refund it.
                if pay.partner_id and not pay.is_advance_payment:
                    pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
                elif pay.is_advance_payment:
                    pay.destination_account_id = pay.partner_id.with_company(
                        pay.company_id).property_account_payable_advance_id.id
                else:
                    pay.destination_account_id = self.env['account.account'].search([
                        ('company_id', '=', pay.company_id.id),
                        ('user_type_id.name', 'in', ('Prepayments','Payable'))
                    ], limit=1)

    option_select_invoices = fields.Boolean(default=False, store=True, string='Invoices select')
    withold_method = fields.Selection([('itbis', 'ITBIS'),
         ('isr', 'ISR'),('itbis_isr', 'ITBIS e ISR'),('itbis_tccomision', 'ITBIS y Comisiones TC'),('default', 'Ninguno')], store=True, default='default', required=True, string="Retencion de impuestos")
    withold_itbis_select = fields.Many2one('account.tax', string='Retencion de ITBIS', store=True,
        compute="retention_domains")
    withold_isr_select = fields.Many2one('account.tax', string='Retencion de ISR', store=True,
        compute="retention_domains")
    withold_tc_select = fields.Many2one('account.tax', string='Retencion de Comisiones Tarjeta', store=True,
                                         compute="retention_domains")
    withold_itbis_amount = fields.Monetary(store=True,currency_field='currency_id')
    withold_isr_amount = fields.Monetary(store=True,currency_field='currency_id')
    withold_tc_amount = fields.Monetary(store=True, currency_field='currency_id')
    payment_invoice_ids = fields.One2many('account.payment.invoice', 'payment_id',string="Customer Invoices")
    is_investor_related = fields.Boolean('Esta relacionado a accionista?', store=True)
    investor_id = fields.Many2one('res.partner', "Accionista", store=True,tracking=True)

    @api.onchange('payment_type','withold_method')
    def retention_domains(self):
        for payment in self:
            if payment.payment_type == 'inbound' and payment.withold_method != 'itbis_tccomision':
                itbis_retention_sale = payment.env['account.tax'].search([('sale_itbis_retention_type', '!=', False),
                                                                   ('type_tax_use', '=', 'sale'), ('company_id', '=', self.env.company.id)])
                itbis_retention_sale_mapped = itbis_retention_sale.mapped('id')
                isr_retention_sale = self.env['account.tax'].search([('tax_group_id.name', '=', 'ISR'),
                                                                 ('type_tax_use', '=', 'sale'), ('company_id', '=', self.env.company.id)])
                isr_retention_sale_mapped = isr_retention_sale.mapped('id')


                return {
                    'domain': {
                    'withold_itbis_select': [('id', '=', itbis_retention_sale_mapped)],
                    'withold_isr_select': [('id', '=', isr_retention_sale_mapped)],

                    },
                }
            elif payment.payment_type == 'inbound' and payment.withold_method == 'itbis_tccomision':
                itbis_retention_sale = payment.env['account.tax'].search(['|', ('sale_itbis_retention_type', '=', '01'),('is_tc_extra', '=', True),
                                                                             '&',('type_tax_use', '=', 'sale'),
                                                                          ('company_id', '=', self.env.company.id)])
                itbis_retention_sale_mapped = itbis_retention_sale.mapped('id')

                tc_retention_sale = self.env['account.tax'].search(
                    [('is_tc_comision', '=', True), ('company_id', '=', self.env.company.id)])
                tc_retention_sale_mapped = tc_retention_sale.mapped('id')

                return {
                    'domain': {
                    'withold_itbis_select': [('id', '=', itbis_retention_sale_mapped)],
                    'withold_tc_select': [('id', '=', tc_retention_sale_mapped)],

                    },
                }

            elif payment.payment_type == 'outbound':
                itbis_retention_purchase = self.env['account.tax'].search(
                    [('purchase_itbis_retention_type', '!=', False),
                    ('type_tax_use', '=', 'purchase'), ('company_id', '=', self.env.company.id)])
                itbis_retention_purchase_mapped = itbis_retention_purchase.mapped('id')
                isr_retention_purchase = self.env['account.tax'].search(
                    [('isr_retention_type', '!=', False),
                    ('type_tax_use', '=', 'purchase'), ('company_id', '=', self.env.company.id)])
                # raise UserError(_("%s", isr_retention_purchase))
                isr_retention_purchase_mapped = isr_retention_purchase.mapped('id')

                return {
                'domain': {
                    'withold_itbis_select': [('id', '=', itbis_retention_purchase_mapped)],
                    'withold_isr_select': [('id', '=', isr_retention_purchase_mapped)],
                    'withold_tc_select': [('id', '=', 10000000)],

                    },
                }

    def _create_paired_internal_transfer_payment(self):
        ''' When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        '''
        return


    def _prepare_move_line_default_vals(self, vals={}, write_off_line_vals=None):
        # line_vals_list = super(AccountPayment, self)._prepare_move_line_default_vals(
        #     write_off_line_vals=write_off_line_vals)
        # raise UserError(_("%s.", vals))
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}
        withold_itbis_lines = {}
        withold_isr_lines = {}
        withold_tc_lines = {}
        updated_amount_to_journal = 0.0
        updated_amount_original = 0.0
        updated_amount = 0.0
        itbis_withhold = self.withold_itbis_amount if self.withold_itbis_amount or self.withold_itbis_amount > 0 else 0.0
        isr_withhold = self.withold_isr_amount if self.withold_isr_amount or self.withold_isr_amount > 0 else 0.0
        tc_withhold = self.withold_tc_amount if self.withold_tc_amount or self.withold_tc_amount > 0 else 0.0

        journal_id = self.env['account.journal'].search(
            [('id', '=', vals.get('journal_id', self.journal_id.id))])

        if self.withold_isr_select or self.withold_itbis_select or self.withold_tc_select:

            if self.withold_itbis_amount > 0.0 and self.payment_type == 'inbound':
                        withold_itbis_select = self.withold_itbis_select.invoice_repartition_line_ids[1].account_id.id
                        withold_itbis_name = self.withold_itbis_select.name
                        withold_itbis_lines = {'debit': self.currency_id._convert(self.withold_itbis_amount, self.company_id.currency_id, self.company_id, self.date), 'amount_currency': self.withold_itbis_amount, 'type':'inbound_itbis_retention',
                                               'withold_itbis_select': withold_itbis_select,'withold_itbis_name':withold_itbis_name}


            if self.withold_itbis_amount > 0.0 and self.payment_type == 'outbound':
                        withold_itbis_select = self.withold_itbis_select.invoice_repartition_line_ids[1].account_id.id
                        withold_itbis_name = self.withold_itbis_select.name
                        withold_itbis_lines = {'credit': self.currency_id._convert(self.withold_itbis_amount, self.company_id.currency_id, self.company_id, self.date), 'amount_currency': - self.withold_itbis_amount, 'type':'outbound_itbis_retention',
                                               'withold_itbis_select': withold_itbis_select,'withold_itbis_name':withold_itbis_name}



            if self.withold_isr_amount > 0.0 and self.payment_type == 'inbound':
                        withold_isr_select = self.withold_isr_select.invoice_repartition_line_ids[1].account_id.id
                        withold_isr_name = self.withold_isr_select.name
                        withold_isr_lines = {'debit': self.currency_id._convert(self.withold_isr_amount, self.company_id.currency_id, self.company_id, self.date), 'amount_currency': self.withold_isr_amount, 'type': 'inbound_isr_retention',
                                               'withold_isr_select': withold_isr_select,'withold_isr_name':withold_isr_name}



            if self.withold_isr_amount > 0.0 and self.payment_type == 'outbound':
                        withold_isr_select = self.withold_isr_select.invoice_repartition_line_ids[1].account_id.id
                        withold_isr_name = self.withold_isr_select.name
                        withold_isr_lines = {'credit': self.currency_id._convert(self.withold_isr_amount, self.company_id.currency_id, self.company_id, self.date), 'amount_currency': - self.withold_isr_amount, 'type': 'outbound_isr_retention',
                                               'withold_isr_select': withold_isr_select,'withold_isr_name':withold_isr_name} 
                
            if self.withold_tc_amount > 0.0 and self.payment_type == 'inbound':
                        withold_tc_select = self.withold_tc_select.invoice_repartition_line_ids[1].account_id.id
                        withold_tc_name = self.withold_tc_select.name
                        withold_tc_lines = {'debit': self.currency_id._convert(self.withold_tc_amount, self.company_id.currency_id, self.company_id, self.date), 'amount_currency': self.withold_tc_amount, 'type': 'inbound_tc_retention',
                                               'withold_tc_select': withold_tc_select,'withold_tc_name':withold_tc_name}



            if self.withold_tc_amount > 0.0 and self.payment_type == 'outbound':
                        withold_tc_select = self.withold_tc_select.invoice_repartition_line_ids[1].account_id.id
                        withold_tc_name = self.withold_tc_select.name
                        withold_tc_lines = {'credit': self.withold_tc_amount, 'amount_currency': - self.withold_tc_amount, 'type': 'outbound_tc_retention',
                                               'withold_tc_select': withold_tc_select,'withold_tc_name':withold_tc_name}  

        if vals:

            if 'amount' in vals:
                updated_amount = self.currency_id._convert(vals['amount'], self.company_id.currency_id, self.company_id, self.date)
                updated_amount_original = vals['amount']
            if 'amount_to_journal' in vals:
                updated_amount_to_journal = self.to_journal_id.currency_id._convert(vals['amount_to_journal'], self.company_id.currency_id, self.company_id, self.date)


            if 'withold_itbis_amount' in vals:

                if vals['withold_itbis_amount'] > 0.0 and self.payment_type == 'inbound':
                        withold_itbis_select = self.env['account.tax'].search([('id', '=', vals['withold_itbis_select'])]) if 'withold_itbis_select' in vals else self.withold_itbis_select
                        withold_itbis_name = withold_itbis_select.name
                        withold_itbis_lines = {'debit': self.currency_id._convert(vals['withold_itbis_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': vals['withold_itbis_amount'], 'type':'inbound_itbis_retention',
                                               'withold_itbis_select': withold_itbis_select.invoice_repartition_line_ids[1].account_id.id, 'withold_itbis_name': withold_itbis_name}
                        itbis_withhold =  vals['withold_itbis_amount']

                if vals['withold_itbis_amount'] == 0 and self.payment_type == 'inbound':
                        withold_itbis_lines = {}
                        itbis_withhold = 0.0


                if vals['withold_itbis_amount'] > 0.0 and self.payment_type == 'outbound':
                        withold_itbis_select = self.env['account.tax'].search([('id', '=', vals['withold_itbis_select'])]) if 'withold_itbis_select' in vals else self.withold_itbis_select
                        withold_itbis_name = withold_itbis_select.name
                        withold_itbis_lines = {'credit': self.currency_id._convert(vals['withold_itbis_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': - vals['withold_itbis_amount'], 'type':'outbound_itbis_retention',
                                               'withold_itbis_select': withold_itbis_select.invoice_repartition_line_ids[1].account_id.id, 'withold_itbis_name': withold_itbis_name}
                        itbis_withhold =  vals['withold_itbis_amount']

                if vals['withold_itbis_amount'] == 0 and self.payment_type == 'outbound':
                        withold_itbis_lines = {}
                        itbis_withhold = 0.0

            if 'withold_isr_amount' in vals:

                if vals['withold_isr_amount'] > 0.0 and self.payment_type == 'inbound':
                        withold_isr_select = self.env['account.tax'].search([('id', '=', vals['withold_isr_select'])]) if 'withold_isr_select' in vals else self.withold_isr_select
                        withold_isr_name = withold_isr_select.name
                        withold_isr_lines = {'debit': self.currency_id._convert(vals['withold_isr_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': vals['withold_isr_amount'], 'type': 'inbound_isr_retention',
                                               'withold_isr_select': withold_isr_select.invoice_repartition_line_ids[1].account_id.id, 'withold_isr_name': withold_isr_name}
                        isr_withhold = vals['withold_isr_amount']

                if vals['withold_isr_amount'] == 0 and self.payment_type == 'inbound':
                        withold_isr_lines = {}
                        isr_withhold = 0.0

                if vals['withold_isr_amount'] > 0.0 and self.payment_type == 'outbound':
                        withold_isr_select = self.env['account.tax'].search([('id', '=', vals['withold_isr_select'])]) if 'withold_isr_select' in vals else self.withold_isr_select
                        withold_isr_name = withold_isr_select.name
                        withold_isr_lines = {'credit': self.currency_id._convert(vals['withold_isr_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': - vals['withold_isr_amount'], 'type': 'outbound_isr_retention',
                                               'withold_isr_select': withold_isr_select.invoice_repartition_line_ids[1].account_id.id, 'withold_isr_name': withold_isr_name}
                        isr_withhold = vals['withold_isr_amount']

                if vals['withold_isr_amount'] == 0 and self.payment_type == 'outbound':
                        withold_isr_lines = {}
                        isr_withhold = 0.0
            
            if 'withold_tc_amount' in vals:

                if vals['withold_tc_amount'] > 0.0 and self.payment_type == 'inbound':
                        withold_tc_select = self.env['account.tax'].search([('id', '=', vals['withold_tc_select'])]) if 'withold_tc_select' in vals else self.withold_tc_select
                        withold_tc_name = withold_tc_select.name
                        withold_tc_lines = {'debit': self.currency_id._convert(vals['withold_tc_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': vals['withold_tc_amount'], 'type': 'inbound_tc_retention',
                                               'withold_tc_select': withold_tc_select.invoice_repartition_line_ids[1].account_id.id, 'withold_tc_name': withold_tc_name}
                        tc_withhold = vals['withold_tc_amount']

                if vals['withold_tc_amount'] == 0 and self.payment_type == 'inbound':
                        withold_tc_lines = {}
                        tc_withhold = 0.0

                if vals['withold_tc_amount'] > 0.0 and self.payment_type == 'outbound':
                        withold_tc_select = self.env['account.tax'].search([('id', '=', vals['withold_tc_select'])]) if 'withold_tc_select' in vals else self.withold_tc_select
                        withold_tc_name = withold_tc_select.name
                        withold_tc_lines = {'credit': self.currency_id._convert(vals['withold_tc_amount'], self.company_id.currency_id, self.company_id, self.date), 'amount_currency': - vals['withold_tc_amount'], 'type': 'outbound_tc_retention',
                                               'withold_tc_select': withold_tc_select.invoice_repartition_line_ids[1].account_id.id, 'withold_tc_name': withold_tc_name}
                        tc_withhold = vals['withold_tc_amount']

                if vals['withold_tc_amount'] == 0 and self.payment_type == 'outbound':
                        withold_tc_lines = {}
                        tc_withhold = 0.0
            


        for accounts in self.withold_itbis_select.invoice_repartition_line_ids.account_id:
            if not any (accounts):
                    raise UserError(_('Por favor configurar una cuenta para el ITBIS retenido.'))
        for accounts in self.withold_isr_select.invoice_repartition_line_ids.account_id:
            if not any (accounts):
                    raise UserError('Por favor configurar una cuenta para el ISR retenido.')

        if (not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id) \
                and not self.journal_id.default_account_id.id:
            raise UserError(_(
                    "No puede crear un pago sin una cuenta de salida/entrada asignada  "
                    "o una cuenta defecto seteada en el diario: %s."
                ) % self.journal_id.display_name)

            # Compute amounts.
        write_off_amount = write_off_line_vals.get('amount', 0.0)


        if self.payment_type == 'inbound' and (self.is_internal_transfer == False or self.internal_transfer_type != 'j_to_j'):
                # Receive money.
            counterpart_amount = -self.amount if updated_amount == 0.0 else - updated_amount_original
            write_off_amount *= -1

        elif self.payment_type == 'outbound' and (self.is_internal_transfer == False or self.internal_transfer_type != 'j_to_j'):
                # Send money.
            counterpart_amount = self.amount if updated_amount == 0.0 else updated_amount_original

        elif self.payment_type == 'inbound' and (self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_j'):
            internal_amount = - self.amount_to_journal if updated_amount_to_journal == 0.0 else updated_amount_to_journal
            counterpart_amount = -self.amount if updated_amount == 0.0 else - updated_amount_original

        elif self.payment_type == 'outbound' and (self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_j'):
            internal_amount = self.amount_to_journal if updated_amount_to_journal == 0.0 else updated_amount_to_journal
            counterpart_amount = self.amount if updated_amount == 0.0 else updated_amount_original

        else:

            counterpart_amount = 0.0
            write_off_amount = 0.0

        if self.is_internal_transfer == False or self.internal_transfer_type != 'j_to_j':
            balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
        elif (self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_j') and \
                self.currency_id != self.journal_id.company_id.currency_id:
            balance = internal_amount

        elif (self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_j') and \
                self.currency_id == self.journal_id.company_id.currency_id:
            balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
        counterpart_amount_currency = counterpart_amount
        write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id,
                                                      self.date)
        write_off_amount_currency = write_off_amount
        currency_id = self.currency_id.id




            # Compute a default label to set on the journal items.

        payment_display_name = {
                'outbound-customer': _("Devuelta de cliente"),
                'inbound-customer': _("Pago de cliente"),
                'outbound-supplier': _("Pago de proveedor"),
                'inbound-supplier': _("Devuelta de proveedor"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
                payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
                self.amount + itbis_withhold + isr_withhold + tc_withhold if not vals else updated_amount + itbis_withhold + isr_withhold + tc_withhold,
                self.currency_id,
                self.date,
                partner=self.partner_id,
        )


        if self.is_internal_transfer and self.internal_transfer_type == 'j_to_j':
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transferencia a %s, monto de %s', self.journal_id.name,
                self.amount + itbis_withhold + isr_withhold + tc_withhold if not vals else updated_amount + itbis_withhold + isr_withhold + tc_withhold)
                default_line_name = _('Transferencia a %s, monto de %s', self.journal_id.name,
                                      self.amount + itbis_withhold + isr_withhold + tc_withhold if not vals else updated_amount + itbis_withhold + isr_withhold + tc_withhold)
            else:  # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transferencia a %s, monto de %s', self.journal_id.name,
                self.amount + itbis_withhold + isr_withhold + tc_withhold if not vals else updated_amount + itbis_withhold + isr_withhold + tc_withhold)
                default_line_name = _('Transferencia a %s, monto de %s', self.journal_id.name,
                self.amount + itbis_withhold + isr_withhold + tc_withhold if not vals else updated_amount + itbis_withhold + isr_withhold + tc_withhold)
        else:
            liquidity_line_name = self.payment_reference

        liquidity_line_account = (self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id) \
                                    if self.journal_id.payment_debit_account_id or self.journal_id.payment_credit_account_id else self.journal_id.default_account_id.id

        # Custom Code
        # if self.is_internal_transfer == True and self.internal_transfer_type == 'a_to_a':
        #     liquidity_line_account = self.from_account_id.id

        # if self.is_internal_transfer == True and self.internal_transfer_type == 'a_to_j':
        #     liquidity_line_account = self.from_account_id.id

        if self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_a':
            if self.payment_type == 'inbound' and self.journal_id.type in ('bank','cash'):
                liquidity_line_account = self.journal_id.payment_debit_account_id.id if self.journal_id.payment_debit_account_id else self.journal_id.default_account_id.id
            elif self.payment_type == 'outbound' and self.journal_id.type in ('bank','cash'):
                liquidity_line_account = self.journal_id.payment_credit_account_id.id if self.journal_id.payment_credit_account_id else self.journal_id.default_account_id.id
            elif self.payment_type == 'inbound' and self.journal_id.type not in ('bank','cash'):
                liquidity_line_account = self.journal_id.default_account_id.id
            elif self.payment_type == 'outbound' and self.journal_id.type not in ('bank','cash'):
                liquidity_line_account = self.journal_id.default_account_id.id
                
        if self.is_internal_transfer == True and self.internal_transfer_type == 'j_to_j':
            if self.payment_type == 'inbound' and self.journal_id.type in ('bank', 'cash'):
                liquidity_line_account = self.journal_id.payment_debit_account_id.id if self.journal_id.payment_debit_account_id else self.journal_id.default_account_id.id
            elif self.payment_type == 'outbound' and self.journal_id.type in ('bank', 'cash'):
                liquidity_line_account = self.journal_id.payment_credit_account_id.id if self.journal_id.payment_credit_account_id else self.journal_id.default_account_id.id
            elif self.payment_type == 'inbound' and self.journal_id.type not in ('bank', 'cash'):
                liquidity_line_account = self.journal_id.default_account_id.id
            elif self.payment_type == 'outbound' and self.journal_id.type not in ('bank', 'cash'):
                liquidity_line_account = self.journal_id.default_account_id.id



        investor = None
        is_investor = None
        if vals:
            if 'investor_id' in vals:
                investor = vals['investor_id']
            if 'is_investor_related' in vals:
                is_investor = vals['is_investor_related']
        if investor == None:
            investor = self.investor_id.id
        if is_investor == None:
            is_investor = self.is_investor_related
        
        if withold_itbis_lines and not withold_isr_lines:


                if withold_itbis_lines.get('type') == 'inbound_itbis_retention':

                    line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': (balance < 0.0 and -balance or 0.0),
                    'credit': balance > 0.0 and balance or 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account},
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency - withold_itbis_lines.get('amount_currency') if currency_id else 0.0,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': balance - withold_itbis_lines.get('debit') < 0.0 and -balance + withold_itbis_lines.get('debit') or 0.0,
                    'partner_id': self.partner_id.id if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                },
                    {
                        'name': str(self.partner_id.name) + ", ITBIS :" + withold_itbis_lines.get('withold_itbis_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit': withold_itbis_lines.get('debit') or 0.0,
                        'credit': 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_itbis_lines.get('withold_itbis_select')
                    }
            ]



                if withold_itbis_lines.get('type') == 'outbound_itbis_retention':
                    # Receivable / Payable.
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': -counterpart_amount_currency,
                            'currency_id': currency_id,
                            'debit': (balance < 0.0 and -balance or 0.0),
                            'credit': (balance > 0.0 and balance or 0.0),
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': counterpart_amount_currency - withold_itbis_lines.get('amount_currency') if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance + withold_itbis_lines.get('credit') > 0.0 and balance + withold_itbis_lines.get('credit') or 0.0,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'partner_id': self.partner_id.id if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                            'account_id': self.destination_account_id.id,
                        },

                        {
                    'name': str(self.partner_id.name) + ", ITBIS :" + withold_itbis_lines.get('withold_itbis_name'),
                    'date_maturity': self.date,
                    'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': withold_itbis_lines.get('credit') or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': withold_itbis_lines.get('withold_itbis_select')
                    }
                    ]

        if withold_isr_lines and not withold_itbis_lines:

                if withold_isr_lines.get('type') == 'inbound_isr_retention':

                    line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': (balance < 0.0 and -balance or 0.0),
                    'credit': balance > 0.0 and balance or 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account},
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency - withold_isr_lines.get('amount_currency') if currency_id else 0.0,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': balance - withold_isr_lines.get('debit') < 0.0 and -balance + withold_isr_lines.get('debit') or 0.0,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                },
                    {
                        'name': str(self.partner_id.name) + ", ISR :" + withold_isr_lines.get('withold_isr_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_isr_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit': withold_isr_lines.get('debit') or 0.0,
                        'credit': 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_isr_lines.get('withold_isr_select')
                    }
            ]



                if withold_isr_lines.get('type') == 'outbound_isr_retention':
                    # Receivable / Payable.
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': -counterpart_amount_currency,
                            'currency_id': currency_id,
                            'debit': (balance < 0.0 and -balance or 0.0),
                            'credit': (balance > 0.0 and balance or 0.0),
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': counterpart_amount_currency - withold_isr_lines.get('amount_currency') if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance + withold_isr_lines.get('credit') > 0.0 and balance + withold_isr_lines.get('credit') or 0.0,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                            'account_id': self.destination_account_id.id,
                        },

                        {
                    'name': str(self.partner_id.name) + ", ISR :" + withold_isr_lines.get('withold_isr_name'),
                    'date_maturity': self.date,
                    'amount_currency': withold_isr_lines.get('amount_currency') or 0.0,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': withold_isr_lines.get('credit') or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': withold_isr_lines.get('withold_isr_select')
                    }
                    ]

        if withold_itbis_lines and withold_isr_lines:



            if withold_itbis_lines.get('type') == 'inbound_itbis_retention' and withold_isr_lines.get('type') == 'inbound_isr_retention':

                line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': (balance < 0.0 and -balance or 0.0),
                    'credit': balance > 0.0 and balance or 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account},
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency - withold_itbis_lines.get('amount_currency') - withold_isr_lines.get('amount_currency') if currency_id else 0.0,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': balance - withold_itbis_lines.get('debit') - withold_isr_lines.get('debit') < 0.0 and -balance + withold_itbis_lines.get('debit') + withold_isr_lines.get('debit') or 0.0,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                },
                    {
                        'name': str(self.partner_id.name) + ", ITBIS :" + withold_itbis_lines.get('withold_itbis_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit': withold_itbis_lines.get('debit') or 0.0,
                        'credit': 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_itbis_lines.get('withold_itbis_select')
                    },

                    {
                        'name': str(self.partner_id.name) + ", ISR :" + withold_isr_lines.get('withold_isr_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_isr_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit': withold_isr_lines.get('debit') or 0.0,
                        'credit': 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_isr_lines.get('withold_isr_select')
                    },


                ]

            if withold_itbis_lines.get('type') == 'outbound_itbis_retention' and withold_isr_lines.get('type') == 'outbound_isr_retention':

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': (balance < 0.0 and -balance or 0.0) ,
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency - (withold_itbis_lines.get('amount_currency') + withold_isr_lines.get('amount_currency')) if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + withold_itbis_lines.get('credit') + withold_isr_lines.get('credit') > 0.0 and balance + withold_itbis_lines.get('credit') + withold_isr_lines.get('credit') or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },
                    {
                        'name': str(self.partner_id.name) + ", ITBIS :" + withold_itbis_lines.get('withold_itbis_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit':  0.0,
                        'credit': withold_itbis_lines.get('credit') or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_itbis_lines.get('withold_itbis_select')
                    },

                    {
                        'name': str(self.partner_id.name) + ", ISR :" + withold_isr_lines.get('withold_isr_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_isr_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit':  0.0,
                        'credit': withold_isr_lines.get('credit') or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_isr_lines.get('withold_isr_select')
                    },

                ]

        if (withold_itbis_lines and withold_tc_lines) or withold_tc_lines:


            if (withold_itbis_lines.get('type') == 'inbound_itbis_retention' and withold_tc_lines.get('type') == 'inbound_tc_retention') or withold_tc_lines.get('type') == 'inbound_tc_retention':

                if withold_itbis_lines == {}:
                    line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': (balance < 0.0 and -balance or 0.0),
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account},
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency - withold_tc_lines.get('amount_currency') if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance - withold_tc_lines.get('debit') < 0.0 and -balance + withold_tc_lines.get('debit') or 0.0,
                        'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                        or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                        {
                            'name': str(self.partner_id.name or 'SN no asignado') + ", TC :" + withold_tc_lines.get('withold_tc_name'),
                            'date_maturity': self.date,
                            'amount_currency': withold_tc_lines.get('amount_currency') or 0.0,
                            'currency_id': currency_id,
                            'debit': withold_tc_lines.get('debit') or 0.0,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id,
                            'account_id': withold_tc_lines.get('withold_tc_select')
                        },


                    ]

                else:
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': -counterpart_amount_currency,
                            'currency_id': currency_id,
                            'debit': (balance < 0.0 and -balance or 0.0),
                            'credit': balance > 0.0 and balance or 0.0,
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': counterpart_amount_currency - withold_itbis_lines.get(
                                'amount_currency') - withold_tc_lines.get('amount_currency') if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                            'credit': balance - withold_itbis_lines.get('debit') - withold_tc_lines.get(
                                'debit') < 0.0 and -balance + withold_itbis_lines.get('debit') + withold_tc_lines.get(
                                'debit') or 0.0,
                            'partner_id': self.partner_id.id if (
                                                                            not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                                                                or self.journal_id.type == 'general' else investor,
                            'account_id': self.destination_account_id.id,
                        },
                        {
                            'name': str(
                                self.partner_id.name or 'SN no asignado') + ", ITBIS :" + withold_itbis_lines.get(
                                'withold_itbis_name'),
                            'date_maturity': self.date,
                            'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                            'currency_id': currency_id,
                            'debit': withold_itbis_lines.get('debit') or 0.0,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id,
                            'account_id': withold_itbis_lines.get('withold_itbis_select')
                        },

                        {
                            'name': str(self.partner_id.name or 'SN no asignado') + ", TC :" + withold_tc_lines.get(
                                'withold_tc_name'),
                            'date_maturity': self.date,
                            'amount_currency': withold_tc_lines.get('amount_currency') or 0.0,
                            'currency_id': currency_id,
                            'debit': withold_tc_lines.get('debit') or 0.0,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id,
                            'account_id': withold_tc_lines.get('withold_tc_select')
                        },

                    ]


            if withold_itbis_lines.get('type') == 'outbound_itbis_retention' and withold_tc_lines.get('type') == 'outbound_tc_retention':

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': (balance < 0.0 and -balance or 0.0) ,
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency - (withold_itbis_lines.get('amount_currency') + withold_tc_lines.get('amount_currency')) if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + withold_itbis_lines.get('credit') + withold_tc_lines.get('credit') > 0.0 and balance + withold_itbis_lines.get('credit') + withold_tc_lines.get('credit') or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },
                    {
                        'name': str(self.partner_id.name or 'SN no asignado') + ", ITBIS :" + withold_itbis_lines.get('withold_itbis_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_itbis_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit':  0.0,
                        'credit': withold_itbis_lines.get('credit') or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_itbis_lines.get('withold_itbis_select')
                    },

                    {
                        'name': str(self.partner_id.name or 'SN no asignado') + ", TC :" + withold_tc_lines.get('withold_tc_name'),
                        'date_maturity': self.date,
                        'amount_currency': withold_tc_lines.get('amount_currency') or 0.0,
                        'currency_id': currency_id,
                        'debit':  0.0,
                        'credit': withold_tc_lines.get('credit') or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': withold_tc_lines.get('withold_tc_select')
                    },

                ]
        
        if withold_itbis_lines == {} and withold_isr_lines == {} and withold_tc_lines == {} and self.parent_internal_transfer:


            if updated_amount > 0.0 and updated_amount_to_journal == 0.0:

                if self.payment_type == 'inbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': updated_amount_original,
                    'currency_id': currency_id,
                    'debit': updated_amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else - updated_amount_original,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': (balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0)  if not vals else updated_amount,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                    ]


                if self.payment_type == 'outbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -updated_amount_original,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': updated_amount,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else updated_amount_original,
                    'currency_id': currency_id,
                    'debit': (balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0) if not vals else updated_amount,
                    'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                    },

                    ]


            if updated_amount_to_journal > 0.0 and updated_amount == 0.0:

                if self.payment_type == 'inbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': self.amount,
                    'currency_id': currency_id,
                    'debit': updated_amount_to_journal,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else - self.amount,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': (balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0)  if not vals else updated_amount_to_journal,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                    ]

                if self.payment_type == 'outbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -self.amount,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': updated_amount_to_journal,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else self.amount,
                    'currency_id': currency_id,
                    'debit': (balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0) if not vals else updated_amount_to_journal,
                    'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                    },

                    ]

            if updated_amount_to_journal > 0.0 and updated_amount > 0.0:
                currency_amount = 0.0
                local_amount = 0.0

                if self.currency_id == self.company_id.currency_id:
                    local_amount = updated_amount
                    currency_amount = updated_amount
                elif self.currency_id != self.company_id.currency_id and self.to_journal_id.currency_id == self.company_id.currency_id:
                    local_amount = updated_amount_to_journal
                    currency_amount = updated_amount_original
                elif self.currency_id != self.company_id.currency_id and self.to_journal_id.currency_id != self.company_id.currency_id:
                    local_amount = 0.0
                    currency_amount = updated_amount_original


                if self.payment_type == 'inbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': currency_amount,
                    'currency_id': currency_id,
                    'debit': local_amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else - currency_amount,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': (balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0)  if not vals else local_amount,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                    ]

                if self.payment_type == 'outbound':

                    line_vals_list = [
                    # Liquidity line.
                    {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -currency_amount,
                    'currency_id': currency_id,
                    'debit': 0.0,
                    'credit': local_amount,
                    'partner_id': self.partner_id.id if not is_investor else investor,
                    'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': (counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else currency_amount,
                    'currency_id': currency_id,
                    'debit': (balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0) if not vals else local_amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                    'account_id': self.destination_account_id.id,
                    },

                    ]
                # raise UserError(_("%s", line_vals_list))

            else:


                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account    },
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'partner_id': self.partner_id.id  if (not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                    or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                ]





        elif withold_itbis_lines == {} and withold_isr_lines == {} and withold_tc_lines == {} and self.child_internal_transfer:

            parent_debit = 0.0
            parent_credit = 0.0
            parent_move = self.env['account.move'].search([('id', '=', self.related_payment_transfer.move_id.id)])
            for move in parent_move:
                for line in move.line_ids:
                    parent_debit += line.debit
                    parent_credit += line.credit

            if updated_amount > 0.0 or updated_amount_to_journal > 0.0:


                if self.payment_type == 'inbound':
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': updated_amount_original if updated_amount_original != 0.0 else self.amount,
                            'currency_id': currency_id,
                            'debit': parent_debit,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': ((
                                counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else - updated_amount_original) if updated_amount_original != 0.0 else - self.amount,
                            'currency_id': currency_id,
                            'debit': 0.0,
                            'credit': parent_credit,
                            'partner_id': self.partner_id.id if (
                                                                            not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                                                                or self.journal_id.type == 'general' else investor,
                            'account_id': self.destination_account_id.id,
                        },

                    ]


                if self.payment_type == 'outbound':
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': -updated_amount_original if updated_amount_original != 0.0 else - self.amount,
                            'currency_id': currency_id,
                            'debit': 0.0,
                            'credit': parent_credit,
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': ((
                                counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else updated_amount_original) if updated_amount_original != 0.0 else self.amount,
                            'currency_id': currency_id,
                            'debit': parent_debit,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id if (
                                                                            not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                                                                or self.journal_id.type == 'general' else investor,
                            'account_id': self.destination_account_id.id,
                        },

                    ]

                # raise UserError(_("%s,%s",line_vals_list,vals ))

            else:

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': parent_debit if self.payment_type == 'inbound' else 0.0,
                        'credit': parent_credit if self.payment_type == 'outbound' else 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account},
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': parent_debit if self.payment_type == 'outbound' else 0.0,
                        'credit': parent_credit if self.payment_type == 'inbound' else 0.0,
                        'partner_id': self.partner_id.id if (
                                                                        not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor)
                                                            or self.journal_id.type == 'general' else investor,
                        'account_id': self.destination_account_id.id,
                    },

                ]

        elif withold_itbis_lines == {} and withold_isr_lines == {} and withold_tc_lines == {}:

            if updated_amount > 0.0:

                if self.payment_type == 'inbound':
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': updated_amount_original,
                            'currency_id': currency_id,
                            'debit': updated_amount,
                            'credit': 0.0,
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': (
                                counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else - updated_amount_original,
                            'currency_id': currency_id,
                            'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                            'credit': (
                                        balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0) if not vals else updated_amount,
                            'partner_id': self.partner_id.id if not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor
                            else investor,
                            'account_id': self.destination_account_id.id,
                        },

                    ]

                if self.payment_type == 'outbound':
                    line_vals_list = [
                        # Liquidity line.
                        {
                            'name': liquidity_line_name or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': -updated_amount_original,
                            'currency_id': currency_id,
                            'debit': 0.0,
                            'credit': updated_amount,
                            'partner_id': self.partner_id.id if not is_investor else investor,
                            'account_id': liquidity_line_account},
                        # Receivable / Payable.
                        {
                            'name': self.payment_reference or default_line_name,
                            'date_maturity': self.date,
                            'amount_currency': (
                                counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0) if not vals else updated_amount_original,
                            'currency_id': currency_id,
                            'debit': (
                                        balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0) if not vals else updated_amount,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'partner_id': self.partner_id.id if not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor
                            else investor,
                            'account_id': self.destination_account_id.id,
                        },

                    ]


            else:

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id if not is_investor else investor,
                        'account_id': liquidity_line_account},
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'partner_id': self.partner_id.id if not self.is_internal_transfer and self.internal_transfer_type != 'j_to_a' and not is_investor
                        else investor,
                        'account_id': self.destination_account_id.id,
                    },

                ]


        if write_off_balance and withold_itbis_lines == {} and withold_isr_lines == {} and withold_tc_lines == {} \
                and self.withold_method == 'default':
            _logger.info("Write Off Dict: %s" % (write_off_line_vals))
            line_vals_list.append({
                'name': write_off_line_vals.get('name','') or default_line_name,
                'amount_currency': -write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id',''),
            })

        manual_currency = vals.get('tasa_manual', self.tasa_manual)

        apply_rate = vals.get('currency_id', self.currency_id.id) == vals.get('journal_currency_id', journal_id.currency_id.id) == self.company_id.currency_id.id

        if (self.different_currencies and self.state == 'draft' and apply_rate == False) or (self.state == 'draft' and manual_currency and apply_rate == False):
            difference_debit_credit = 0.0
            count = 0

            for rec in line_vals_list:
                if (self.journal_currency_id == self.company_id.currency_id and self.is_internal_transfer == False) or \
                        (
                                self.is_internal_transfer == True and self.journal_currency_id == self.company_id.currency_id and
                                self.internal_transfer_type == 'j_to_a'):
                    rate = (self.payment_rate if not 'payment_rate' in vals else vals[
                        'payment_rate']) if vals else self.payment_rate
                    if rate != 0.0:
                        rec.update({
                            'debit': rec['amount_currency'] * rate if rec['debit'] != 0.0 else 0.0,
                            'credit': - (rec['amount_currency'] * rate) if rec['credit'] != 0.0 else 0.0,
                        })
                    difference_debit_credit += round(rec['debit'] - rec['credit'], 2)
                    count += 1
                    if count == len(line_vals_list) and rate != 0.0:
                        difference_debit_credit = round(difference_debit_credit, 2)
                        if difference_debit_credit > 0:
                            rec.update({
                                'debit': rec['debit'] - difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] + abs(difference_debit_credit) if rec['credit'] != 0.0 else rec[
                                    'credit'],
                            })
                        if difference_debit_credit < 0:
                            rec.update({
                                'debit': rec['debit'] + difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] - abs(difference_debit_credit) if rec['credit'] != 0.0 else rec[
                                    'credit'],
                            })
                    # raise UserError(_("%s, %s", rate, line_vals_list))

                elif (self.journal_currency_id != self.company_id.currency_id and self.is_internal_transfer == False) or \
                        (
                                self.is_internal_transfer == True and self.journal_currency_id != self.company_id.currency_id and \
                                self.internal_transfer_type == 'j_to_a'):
                    rate = (self.payment_rate if not 'payment_rate' in vals else vals[
                        'payment_rate']) if vals else self.payment_rate
                    if rate == 0.0:
                        rate = 1 / self.currency_id._get_conversion_rate(self.currency_id,
                                                                         self.journal_currency_id,
                                                                         self.company_id,
                                                                         self.date or fields.Date.context_today(
                                                                             rec))

                    # if journal_id_t.id != self.company_id.currency_id.id and currency_id != journal_id_t.id and currency_id != self.company_id.currency_id.id:
                    #     rate = rec['debit'] / journal_amount if rec['debit'] != 0.0 else (rec['credit'] / journal_amount)
                    #     rec.update({
                    #         'amount_currency': rec['debit'] / rate if rec['debit'] != 0.0 else - (rec['credit'] / rate),
                    #         'currency_id': self.journal_currency_id.id,
                    #     })
                    # else:

                    if vals.get('currency_id',self.currency_id) != self.company_id.currency_id:
                        rec.update({
                            'debit': rec['amount_currency'] * rate if rec['amount_currency'] > 0.0 else 0.0,
                            'credit': - rec['amount_currency'] * rate if rec['amount_currency'] < 0.0 else 0.0,
                            'currency_id': currency_id,
                        })
                    else:
                        rec.update({
                            'amount_currency': rec['debit'] / rate if rec['debit'] != 0.0 else - (rec['credit'] / rate),
                            'currency_id': currency_id,
                        })


        elif self.different_currencies_2 and self.state == 'draft' or (
                self.to_journal_id.currency_id == self.currency_id and self.currency_id != self.company_id.currency_id and self.is_internal_transfer):
            difference_debit_credit = 0.0
            count = 0
            for rec in line_vals_list:
                if self.currency_id == self.journal_currency_id and self.internal_transfer_type != 'j_to_j':
                    rate = (self.payment_rate if not 'payment_rate' in vals else vals[
                        'payment_rate']) if vals else self.payment_rate
                    if rate == 0.0:
                        rate = 1 / self.currency_id._get_conversion_rate(self.company_id.currency_id,
                                                                         self.currency_id,
                                                                         self.company_id,
                                                                         self.date or fields.Date.context_today(
                                                                             rec))
                    rec.update({
                        'debit': rec['amount_currency'] * rate if rec['debit'] != 0.0 else 0.0,
                        'credit': - (rec['amount_currency'] * rate) if rec['credit'] != 0.0 else 0.0,
                    })
                    difference_debit_credit += round(rec['debit'] - rec['credit'], 2)
                    count += 1

                    if count == len(line_vals_list) and rate != 0.0:
                        difference_debit_credit = round(difference_debit_credit, 2)
                        if difference_debit_credit > 0:
                            rec.update({
                                'debit': rec['debit'] - difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] + abs(difference_debit_credit) if rec['credit'] != 0.0 else
                                rec[
                                    'credit'],
                            })
                        if difference_debit_credit < 0:
                            rec.update({
                                'debit': rec['debit'] + difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] - abs(difference_debit_credit) if rec['credit'] != 0.0 else
                                rec[
                                    'credit'],
                            })


                elif self.currency_id == self.journal_currency_id and (
                        self.to_journal_id.currency_id == self.currency_id and self.currency_id != self.company_id.currency_id and self.is_internal_transfer):
                    rate = (self.payment_rate if not 'payment_rate' in vals else vals[
                        'payment_rate']) if vals else self.payment_rate
                    if rate == 0.0:
                        rate = 1 / self.currency_id._get_conversion_rate(self.company_id.currency_id,
                                                                         self.currency_id,
                                                                         self.company_id,
                                                                         self.date or fields.Date.context_today(
                                                                             rec))
                    rec.update({
                        'debit': rec['amount_currency'] * rate if rec['debit'] != 0.0 else 0.0,
                        'credit': - (rec['amount_currency'] * rate) if rec['credit'] != 0.0 else 0.0,
                    })
                    difference_debit_credit += round(rec['debit'] - rec['credit'], 2)
                    count += 1

                    if count == len(line_vals_list) and rate != 0.0:
                        difference_debit_credit = round(difference_debit_credit, 2)
                        if difference_debit_credit > 0:
                            rec.update({
                                'debit': rec['debit'] - difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] + abs(difference_debit_credit) if rec['credit'] != 0.0 else
                                rec[
                                    'credit'],
                            })
                        if difference_debit_credit < 0:
                            rec.update({
                                'debit': rec['debit'] + difference_debit_credit if rec['debit'] != 0.0 else rec[
                                    'debit'],
                                'credit': rec['credit'] - abs(difference_debit_credit) if rec['credit'] != 0.0 else
                                rec[
                                    'credit'],
                            })

        balance = 0.0
        currency_balance = self.env['res.currency'].search([('id', '=', currency_id)], limit=1)
        for line in line_vals_list:

            if 'debit' in line and 'credit' in line:
                balance += round(line['debit'], currency_balance.decimal_places) - round(line['credit'],
                                                                                         currency_balance.decimal_places)

        if balance != 0.0:
            if self.payment_type == 'outbound' and 'debit' in line_vals_list[0]:
                line_vals_list[0]['debit'] += round(balance, currency_balance.decimal_places)
            if self.payment_type == 'inbound' and 'debit' in line_vals_list[0]:
                line_vals_list[0]['credit'] += round(balance, currency_balance.decimal_places)

        return line_vals_list


    def _synchronize_to_moves(self, changed_fields, vals={}):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''

        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id','investor_id','amount_to_journal','payment_rate'
        )):

            return

        if vals:
            if 'date' in vals:
                if vals['date'] == self.date:
                    return

        if not vals:
            return

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if writeoff_lines:
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))
                counterpart_amount = counterpart_lines['amount_currency']
                if writeoff_amount > 0.0 and counterpart_amount > 0.0:
                    sign = 1
                else:
                    sign = -1

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount * sign,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(vals,write_off_line_vals=write_off_line_vals)

            # raise UserError(_("%s.", line_vals_list))

            # name1 = False
            # name2 = False
            # for rec in counterpart_lines:
            #     name1 = rec.credit
            #     name2 = rec.credit
            # raise UserError(_("%s,%s", writeoff_lines, liquidity_lines.debit))

            if counterpart_lines:
                line_ids_commands = [
                    (1, liquidity_lines.id, line_vals_list[0]),
                    (1, counterpart_lines.id, line_vals_list[1]),
                ]
            elif writeoff_lines:
                line_ids_commands = [
                    (1, liquidity_lines.id, line_vals_list[0]),
                    (1, writeoff_lines.id, line_vals_list[1]),
                ]

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            writeoff = writeoff_lines
            counterpart = counterpart_lines

            for line in writeoff:
                for counter in counterpart:
                    if line.id != counter.id:
                        line_ids_commands.append((2, line.id))


            if writeoff_lines:

                if len([i for i in line_vals_list if i]) == 3:
                    line_ids_commands.append((0, 0, line_vals_list[2]))
                elif len([i for i in line_vals_list if i]) == 4:
                    line_ids_commands.append((0, 0, line_vals_list[2]))
                    line_ids_commands.append((0, 0, line_vals_list[3]))

            if len([i for i in line_vals_list if i]) > 2 and not writeoff_lines:
                if len([i for i in line_vals_list if i]) == 3:
                    line_ids_commands.append((0, 0, line_vals_list[2]))
                elif len([i for i in line_vals_list if i]) == 4:
                    line_ids_commands.append((0, 0, line_vals_list[2]))
                    line_ids_commands.append((0, 0, line_vals_list[3]))

            # raise UserError(_("%s, %s.", line_ids_commands,self.parent_internal_transfer))

            pay.move_id.write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })



    def action_post(self):
        super(AccountPayment, self).action_post()
        for payment in self:
            if payment.related_payment_transfer and payment.parent_internal_transfer:
                payment.related_payment_transfer.action_post()

            if payment.payment_invoice_ids:
                # raise UserError(_("%s,%s",payment.amount,round(sum(payment.payment_invoice_ids.mapped('reconcile_amount')),2) ))
                if payment.amount < round(sum(payment.payment_invoice_ids.mapped('reconcile_amount')),2):
                    raise UserError(_("The sum of the reconcile amount of listed invoices are greater than payment's amount."))

            for line_id in payment.payment_invoice_ids:
                if not line_id.reconcile_amount:
                    continue
                if line_id.reconcile_amount == line_id.amount_total:
                    self.ensure_one()
                    if payment.payment_type == 'inbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.credit > 0)
                        lines += line_id.invoice_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        lines.reconcile()
                    elif payment.payment_type == 'outbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.debit > 0)
                        lines += line_id.invoice_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        lines.reconcile()
                else:
                    self.ensure_one()
                    if payment.payment_type == 'inbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.credit > 0)
                        lines += line_id.invoice_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        # raise UserError(_("%s", line_id.reconcile_amount + line_id.itbis_withold + line_id.isr_withold + line_id.tc_withold))
                        reconcile_amount = line_id.reconcile_amount + line_id.itbis_withold + line_id.isr_withold + line_id.tc_withold
                        lines.with_context(amount=reconcile_amount).reconcile()
                    elif payment.payment_type == 'outbound':
                        lines = payment.move_id.line_ids.filtered(lambda line: line.debit > 0)
                        lines += line_id.invoice_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                        lines.with_context(amount=line_id.reconcile_amount + line_id.itbis_withold + line_id.isr_withold + line_id.tc_withold).reconcile()
        return True


    @api.onchange('payment_type', 'partner_type', 'partner_id', 'currency_id','payment_invoice_ids.add_invoice')
    def _onchange_to_get_vendor_invoices(self):
        if self.payment_type in ['inbound', 'outbound'] and self.partner_type and self.partner_id and self.currency_id:
            self.payment_invoice_ids = [(6, 0, [])]
            if self.payment_type == 'inbound' and self.partner_type == 'customer':
                invoice_type = 'out_invoice'
            elif self.payment_type == 'outbound' and self.partner_type == 'customer':
                invoice_type = 'out_refund'
            elif self.payment_type == 'outbound' and self.partner_type == 'supplier':
                invoice_type = 'in_invoice'
            else:
                invoice_type = 'in_refund'
            invoice_recs = self.env['account.move'].search([
                ('partner_id', 'child_of', self.partner_id.id),
                ('state', '=', 'posted'),
                ('move_type', '=', invoice_type),
                ('payment_state', '!=', 'paid'),
                ('currency_id', '=', self.currency_id.id)])
            payment_invoice_values = []
            for index,invoice_rec in enumerate(invoice_recs):
                if invoice_rec.amount_residual > 0.0:
                    payment_invoice_values.append([0, 0, {'invoice_id': invoice_rec.id}])
                if self.payment_invoice_ids:
                    payment_invoice_values.append([0, 0, {'add_invoice': self.payment_invoice_ids[index].add_invoice}])
            self.payment_invoice_ids = payment_invoice_values

    @api.onchange('payment_invoice_ids','option_select_invoices')
    def sum_payments_added(self):
        for payment in self:
            added_invoices = 0
            added_withold_itbis = 0
            added_withold_isr = 0
            added_withold_tc = 0
            for invoices in payment.payment_invoice_ids:
                if invoices.add_invoice == True or invoices.reconcile_amount > 0:
                    added_withold_itbis += invoices.itbis_withold
                    added_withold_isr += invoices.isr_withold
                    added_withold_tc += invoices.tc_withold
                    added_invoices += invoices.reconcile_amount
            payment.amount = added_invoices
            payment.withold_itbis_amount = added_withold_itbis
            payment.withold_isr_amount = added_withold_isr
            payment.withold_tc_amount = added_withold_tc



    # @api.onchange('payment_invoice_ids','amount')
    # def read_selected(self):
    #     for payment in self:
    #         selected = 0
    #         for invoices in payment.payment_invoice_ids:
    #             if invoices.add_invoice == False:
    #                 payment.all_selected = False
    #                 selected += 1
    #         if selected == 0:
    #             payment.all_selected = True

    @api.onchange('option_select_invoices')
    def option_select_invoices_change(self):
        for payment in self:
            if payment.option_select_invoices == True:
                added_invoices = 0.0
                added_withold_itbis = 0.0
                added_withold_isr = 0.0
                added_withold_tc = 0.0
                for invoices in payment.payment_invoice_ids:
                    invoices.add_invoice = True
                    added_invoices += invoices.residual - invoices.itbis_withold - invoices.isr_withold - invoices.tc_withold
                    added_withold_itbis += invoices.itbis_withold
                    added_withold_isr += invoices.isr_withold
                    added_withold_tc += invoices.tc_withold
                    if invoices.reconcile_amount == 0.0:
                        invoices.reconcile_amount += invoices.residual - invoices.itbis_withold - invoices.isr_withold - invoices.tc_withold
                payment.amount = added_invoices
                payment.withold_itbis_amount = added_withold_itbis
                payment.withold_isr_amount = added_withold_isr
                payment.withold_tc_amount = added_withold_tc

    @api.onchange('option_select_invoices')
    def option_unselect_invoices_change(self):
        for payment in self:
            if payment.option_select_invoices == False:
                added_invoices = 0.0
                for invoices in payment.payment_invoice_ids:
                    invoices.add_invoice = False
                    invoices.itbis_withold = 0.0
                    invoices.isr_withold = 0.0
                    invoices.reconcile_amount = 0.0
                payment.amount = added_invoices
                payment.withold_itbis_amount = added_invoices
                payment.withold_isr_amount = added_invoices


    @api.onchange('withold_method')
    def empty_retentions(self):
        for payment in self:
               payment.withold_itbis_select = False
               payment.withold_isr_select = False
               payment.withold_tc_select = False
               for invoices in payment.payment_invoice_ids:
                   invoices.itbis_withold = 0.0
                   invoices.isr_withold = 0.0
                   invoices.tc_withold = 0.0

    @api.depends('partner_id')
    def _compute_partner_bank_id(self):
        ''' The default partner_bank_id will be the first available on the partner. '''
        for pay in self:
            available_partner_bank_accounts = pay.partner_id.bank_ids
            if available_partner_bank_accounts and pay.company_id.id in pay.partner_id.bank_ids.company_id.ids:
                pay.partner_bank_id = available_partner_bank_accounts[0]._origin
            else:
                pay.partner_bank_id = False

    @api.onchange('withold_method', 'withold_itbis_select', 'withold_isr_select', 'withold_tc_select','amount','payment_invoice_ids')
    def update_amount_with_retention(self):
        for payment in self:
            if payment.amount > 0:
                added_withold_itbis = 0
                added_withold_isr = 0
                reconcile = 0
                if payment.payment_invoice_ids:
                    for invoices in payment.payment_invoice_ids:
                        if invoices.add_invoice == True or invoices.reconcile_amount > 0:
                            added_withold_itbis += invoices.itbis_withold
                            added_withold_isr += invoices.isr_withold
                            added_withold_isr += invoices.tc_withold
                            if invoices.reconcile_amount == 0.0:
                                invoices.reconcile_amount = invoices.residual - invoices.itbis_withold - invoices.isr_withold - invoices.tc_withold
                            reconcile += invoices.reconcile_amount
                    if reconcile != payment.amount and payment.option_select_invoices:
                        payment.amount = reconcile

                elif payment.withold_method == 'itbis_tccomision' and not payment.payment_invoice_ids:
                    if payment.amount > 0.0:
                        paym = payment.amount
                        itbis = paym * (payment.withold_itbis_select.amount / 100)
                        tc = paym * (payment.withold_tc_select.amount / 100)
                        payment.withold_itbis_amount = - itbis
                        payment.withold_tc_amount = - tc
                        payment.amount = paym + itbis + tc







