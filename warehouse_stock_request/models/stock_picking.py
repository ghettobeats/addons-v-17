# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import api, fields, Command, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools import email_split, float_is_zero, float_repr, float_compare, is_html_empty
from odoo.tools.misc import clean_context, format_date

import re

from odoo.osv import expression
from odoo.tools.misc import formatLang, format_date, parse_date
from odoo.tools import html2plaintext

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    apply_retention = fields.Boolean("Aplicar Retencion?", store=True)

    apply_retention_manual = fields.Boolean("Aplicar Retencion?", store=True, default=True)

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.constrains('aba_routing')
    def _check_aba_routing(self):
        for bank in self:
            if bank.aba_routing and not re.match(r'^\d{1,9}$', bank.aba_routing):
                boole = True
                


class AccountRegisterPaymentsInvoice(models.TransientModel):
    _inherit = "account.register.payments.invoice"

    @api.depends("residual", "invoice_id", "tax_ids")
    def _compute_amount(self):
        for invoice_line in self:
            tax_amount = 0
            for line in invoice_line.invoice_id.invoice_line_ids.filtered(lambda x: x.apply_retention == True):
                for payment_tax in invoice_line.tax_ids:

                    price_wo_discount = line.quantity * line.price_unit
                    price_with_discount = price_wo_discount * (
                        1 - (line.discount / 100.0)
                    )

                    base = round(
                        price_with_discount,
                        invoice_line.currency_id.decimal_places,
                    )

                    if (
                        payment_tax.l10n_do_reconcile_tax_base == "line_tax"
                        and line.price_total - line.price_subtotal
                    ) or payment_tax.l10n_do_reconcile_tax_base == "line_subtotal":
                        tax_amount += payment_tax._compute_amount(
                            base, line.price_unit, line.quantity
                        )

            invoice_line.amount = invoice_line.residual - tax_amount * -1

    @api.constrains("tax_ids", "invoice_id")
    def _check_tax_ids(self):
        for invoice_line in self:
            if any(
                [
                    t
                    for t in invoice_line.tax_ids
                    if t in invoice_line.invoice_id.invoice_line_ids.mapped("tax_ids")
                ]
            ):
                raise UserError(
                    _(
                        "Cannot apply a tax already included in invoice %s"
                        % invoice_line.invoice_id.l10n_do_fiscal_number
                    )
                )

            if len(invoice_line.tax_ids.mapped("tax_group_id")) < len(
                invoice_line.tax_ids
            ):
                raise UserError(
                    _(
                        "Cannot apply multiple taxes of same group in "
                        "invoice %s" % invoice_line.invoice_id.l10n_do_fiscal_number
                    )
                )

class AccountReconciliation(models.AbstractModel):
    _inherit = 'account.reconciliation.widget'

    @api.model
    def _get_search_domain(self, search_str=''):
        ''' Get the domain to be applied on the account.move.line when the user is typing
        something on the search bar.
        :param search_str:  The search bar content as a string.
        :return:            A applicable domain on the account.move.line model.
        '''
        search_str = search_str.strip()
        if not search_str:
            return []

        str_domain = self._str_domain_for_mv_line(search_str)
        if search_str[0] in ['-', '+']:
            try:
                amounts_str = search_str.split('|')
                for amount_str in amounts_str:
                    amount = amount_str[0] == '-' and float(amount_str) or float(amount_str[1:])
                    amount_domain = [
                        '|', ('amount_residual', '=', amount),
                        '|', ('amount_residual_currency', '=', amount),
                        '|', (amount_str[0] == '-' and 'credit' or 'debit', '=', float(amount_str[1:])),
                        ('amount_currency', '=', amount),
                    ]
                    str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
        else:
            try:
                amount = float(search_str)
                amount_domain = [
                    '|', ('amount_residual', '=', amount),
                    '|', ('amount_residual_currency', '=', amount),
                    '|', ('amount_residual', '=', -amount),
                    '|', ('amount_residual_currency', '=', -amount),
                    '&', ('account_id.internal_type', '=', 'liquidity'),
                    '|', '|', '|', ('debit', '=', amount), ('credit', '=', amount), ('amount_currency', '=', amount), ('amount_currency', '=', -amount),
                ]
                str_domain = expression.OR([str_domain, amount_domain])
            except:
                pass
                
        
        payment_id = self.env['account.payment']

        if hasattr(payment_id,'x_lote_moneda_extranjera'):
            return expression.OR([str_domain, ['|','|',('partner_id.name', 'ilike', search_str),('payment_id.numero_de_libramiento', 'ilike', search_str),('payment_id.x_lote_moneda_extranjera', 'ilike', search_str)]])
        else:
            return expression.OR([str_domain, ['|',('partner_id.name', 'ilike', search_str),('payment_id.numero_de_libramiento', 'ilike', search_str)]])

class AccountInvoice(models.Model):
    _inherit = 'account.asset'

    state = fields.Selection([('model', 'Model'), ('draft', 'Recepcion'),('codificacion_entrenga', 'Codificacion y Entrega'), ('open', 'Validado y En Proceso'), ('paused', 'Pausado'), 
                              ('close', 'Cerrado')], 'Status', copy=False, default='draft',
        help="When an asset is created, the status is 'Draft'.\n"
            "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
            "The 'On Hold' status can be set manually when you want to pause the depreciation of an asset for some time.\n"
            "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status.")
            
            
    

    def marcar_clasificacion_entrega(self):
        for rec in self:
            rec.write({'state':'codificacion_entrenga'})


class HrExpense(models.Model):
    _inherit = "hr.expense.sheet"
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('rev_rrhh', 'Revisado RRHH'),
        ('apr_rrhh', 'Aprobado RRHH'),
        ('adm_val', 'Validado Vice ADM'),
        ('apr_adm', 'Aprobado Vice ADM'),
        ('post', 'Posted'),
        ('done', 'Pagado'),
        ('aut_fin', 'Autorizado Financiero'),
        ('rev_ad', 'Revisión Auditoría'),
        ('firma_orden_pago_vice_adm', 'Firma Vice ADM'),
        ('desemb', 'Desembolso'),
        ('cancel', 'Refused')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True)
    
    
    def button_rev_rrhh(self):
        for rec in self:
            rec.write({'state':'rev_rrhh'})
    
    def button_apr_rrhh(self):
        for rec in self:
            rec.write({'state':'apr_rrhh'})
    
    def button_adm_val(self):
        for rec in self:
            rec.write({'state':'adm_val'})
            
    def button_apr_adm(self):
        for rec in self:
            rec.write({'state':'apr_adm'})
    
    def button_aut_fin(self):
        for rec in self:
            rec.write({'state':'aut_fin'})
            
    def button_rev_ad(self):
        for rec in self:
            rec.write({'state':'rev_ad'})

    def button_firma_orden_pago_vice_adm(self):
        for rec in self:
            rec.write({'state':'firma_orden_pago_vice_adm'})
    
    def button_desemb(self):
        for rec in self:
            rec.write({'state':'desemb'})
            
    def action_sheet_move_create(self):
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            if samples.count(False):
                raise UserError(_("You can't mix sample expenses and regular ones"))
            self.write({'state': 'post'})
            return 

        if any(sheet.state != 'apr_adm' for sheet in self):
            raise UserError(_("Solo puede generar las entradas de libro para viaticos aprobados por la Vice Administracion. Estado: %s", self.state))

        if any(not sheet.journal_id for sheet in self):
            raise UserError(_("Specify expense journal to generate accounting entries."))

        expense_line_ids = self.mapped('expense_line_ids')\
            .filtered(lambda r: not float_is_zero(r.total_amount, precision_rounding=(r.currency_id or self.env.company.currency_id).rounding))
        res = expense_line_ids.with_context(clean_context(self.env.context)).action_move_create()

        paid_expenses_company = self.filtered(lambda m: m.payment_mode == 'company_account')
        paid_expenses_company.write({'state': 'done', 'amount_residual': 0.0, 'payment_state': 'paid'})

        paid_expenses_employee = self - paid_expenses_company
        paid_expenses_employee.write({'state': 'post'})

        self.activity_update()
        return res

    def _check_can_approve(self):
        return True

class AccountTax(models.Model):
    _inherit = "account.tax"
    
    tax_partner_id = fields.Many2one('res.partner', 'Proveedor de Impuesto Relacionado')

class AcountMove(models.Model):
    _inherit = "account.move"
    
    retention_payment = fields.Many2many('account.payment', 'dgii_payments_rel', 'move_dgii_id', 'pay_id',
                                   string='Pagos DGII Relacionados a Factura')

    
    
class AccountPayment(models.Model):
    _inherit = "account.payment"

    numero_de_libramiento = fields.Char("Numero de Libramiento",store=True)
    
    is_dgii_payment = fields.Boolean(string="Es pago de DGII", store=True,default=False)
    
    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "include one and only one outstanding payments/receipts account.",
                        move.display_name,
                    ))
                
                if hasattr(pay,'is_advance_payment'):
                    if len(counterpart_lines) != 1 and pay.is_dgii_payment == False and pay.is_advance_payment == False:
                        raise UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "include one and only one receivable/payable account (with an exception of "
                            "internal transfers).",
                            move.display_name,
                        ))
                else:
                    if len(counterpart_lines) != 1 and pay.is_dgii_payment == False:
                        raise UserError(_(
                            "Journal Entry %s is not valid. In order to proceed, the journal items must "
                            "include one and only one receivable/payable account (with an exception of "
                            "internal transfers).",
                            move.display_name,
                        ))

                if writeoff_lines and len(writeoff_lines.account_id) != 1:
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, "
                        "all optional journal items must share the same account.",
                        move.display_name,
                    ))

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same currency.",
                        move.display_name,
                    ))

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "Journal Entry %s is not valid. In order to proceed, the journal items must "
                        "share the same partner.",
                        move.display_name,
                    ))

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

class PaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    numero_de_libramiento = fields.Char("Numero de Libramiento",store=True)

    def _get_move_amounts(self, line, tax):
        
        if hasattr(line,'move_id'):
            invoice_id = line.move_id
        if hasattr(line,'invoice_id'):
            invoice_id = line.invoice_id

        if invoice_id.currency_id != invoice_id.company_id.currency_id:
            monto_base = sum([l.currency_id._convert(l.price_subtotal, l.move_id.company_id.currency_id, l.move_id.company_id, l.move_id.date or fields.Date.context_today(self)) for l in invoice_id.invoice_line_ids.filtered(lambda x: x.apply_retention == True)])
        else:
            monto_base = sum([l.price_subtotal for l in invoice_id.invoice_line_ids.filtered(lambda x: x.apply_retention == True)])

        
        amount = monto_base * (abs(tax.amount) / 100)
        aml_obj = self.env["account.move.line"]

        
        aml_vals = aml_obj._get_fields_onchange_subtotal_model(
            amount,
            invoice_id.move_type,
            invoice_id.currency_id,
            invoice_id.company_id,
            self.payment_date,
        )

        if invoice_id.currency_id != invoice_id.company_id.currency_id:
            return (
                aml_vals["debit"],
                abs(aml_vals["amount_currency"]),
                aml_vals["credit"],
            )

        return aml_vals["debit"], aml_vals["credit"], aml_vals["amount_currency"]
    
    def _create_reconciled_taxes_move(self, invoices):

        aml_mapping = {}
        if invoices:
            journal = self._get_reconciled_payment_move_journal()
            partner_id = invoices[0].partner_id

            move = (
                self.env["account.move"]
                .with_context(default_move_type="entry")
                .create(
                    {
                        "ref": " ".join(
                            [
                                i.l10n_do_fiscal_number
                                for i in invoices
                                if i.l10n_do_fiscal_number
                            ]
                        ),
                        "journal_id": journal,
                        "date": self.payment_date,
                    }
                )
            )

            move_line_vals = []
            for line in self.l10n_do_payments_invoice_ids:
                for tax in line.tax_ids:
                    debit, amount, amount_currency = self._get_move_amounts(line, tax)

                    if amount == 0.0 and debit != 0.0:
                        amount = debit

                    if line.invoice_id.company_id.currency_id != line.invoice_id.currency_id:
                        

                        amount_currency = line.invoice_id.company_id.currency_id._convert(amount, line.invoice_id.currency_id, line.invoice_id.company_id, line.invoice_id.date or fields.Date.context_today(self)) 
                        
                        move_line_vals.extend(
                            [
                                (
                                    0,
                                    0,
                                    {
                                        "move_id": move.id,
                                        "name": tax.name,
                                        "account_id": self._get_tax_account(tax),
                                        "currency_id":line.currency_id.id,
                                        "amount_currency":amount_currency if line.invoice_id.move_type == "out_invoice" else -amount_currency,
                                        "debit": amount
                                        if line.invoice_id.move_type == "out_invoice"
                                        else 0.0,
                                        "credit": amount
                                        if line.invoice_id.move_type == "in_invoice"
                                        else 0.0,
                                        "journal_id": journal,
                                        "partner_id": partner_id.id,
                                    },
                                ),
                                (
                                    0,
                                    0,
                                    {
                                        "move_id": move.id,
                                        "name": tax.name,
                                        "account_id": self._get_invoice_reconcile_move_account(
                                            line.invoice_id
                                        ),
                                        "currency_id":line.currency_id.id,
                                        "amount_currency":amount_currency if line.invoice_id.move_type == "in_invoice" else -amount_currency,
                                        "debit": amount
                                        if line.invoice_id.move_type == "in_invoice"
                                        else 0.0,
                                        "credit": amount
                                        if line.invoice_id.move_type == "out_invoice"
                                        else 0.0,
                                        "journal_id": journal,
                                        "partner_id": partner_id.id,
                                        "l10n_do_reconcile_invoice_id": line.invoice_id.id,
                                    },
                                ),
                            ]
                        )
                    else:
                        
                        move_line_vals.extend(
                            [
                                (
                                    0,
                                    0,
                                    {
                                        "move_id": move.id,
                                        "name": tax.name,
                                        "account_id": self._get_tax_account(tax),
                                        "debit": amount
                                        if line.invoice_id.move_type == "out_invoice"
                                        else 0.0,
                                        "credit": amount
                                        if line.invoice_id.move_type == "in_invoice"
                                        else 0.0,
                                        "journal_id": journal,
                                        "partner_id": partner_id.id,
                                    },
                                ),
                                (
                                    0,
                                    0,
                                    {
                                        "move_id": move.id,
                                        "name": tax.name,
                                        "account_id": self._get_invoice_reconcile_move_account(
                                            line.invoice_id
                                        ),
                                        "debit": amount
                                        if line.invoice_id.move_type == "in_invoice"
                                        else 0.0,
                                        "credit": amount
                                        if line.invoice_id.move_type == "out_invoice"
                                        else 0.0,
                                        "journal_id": journal,
                                        "partner_id": partner_id.id,
                                        "l10n_do_reconcile_invoice_id": line.invoice_id.id,
                                    },
                                ),
                            ]
                        )
                        
                        
                        
            # raise UserError(_("%s , %s", move_line_vals, amount))
            move.line_ids = move_line_vals
            for ml in move.line_ids.filtered(
                lambda l: l.l10n_do_reconcile_invoice_id and not l.reconciled
            ):
                if ml.l10n_do_reconcile_invoice_id not in aml_mapping:
                    aml_mapping[ml.l10n_do_reconcile_invoice_id] = [ml.id]
                else:
                    aml_mapping[ml.l10n_do_reconcile_invoice_id].append(ml.id)

            move._post()

        return aml_mapping
    
    
    def _prepare_tax_payment(self, amount,tax):
        vals = {
                'date': self.payment_date,
                'amount': amount,
                'payment_type': 'outbound',
                'partner_type': self.partner_type if self.partner_type else '',
                'ref': self.communication,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id,
                'partner_id': tax.tax_partner_id.id,
                'partner_bank_id': self.partner_bank_id.id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'is_dgii_payment':True,
                # 'destination_account_id': self._get_tax_account(tax),
            }
        return vals
    
    def _create_payments(self):


        if self.l10n_do_reconcile_taxes and self.payment_type == 'outbound':
            invoices = self.l10n_do_payments_invoice_ids.mapped("invoice_id")

        
            tax_payment = self.env['account.payment']
        
            for line in self.l10n_do_payments_invoice_ids:
                    for tax in line.tax_ids:
                        debit, amount, amount_currency = self._get_move_amounts(line, tax)

                        payment_vals = self._prepare_tax_payment(amount,tax)
                        
                        payment = self.env['account.payment'].sudo().create(payment_vals)
                        
                        for line2 in payment.move_id.line_ids:
                            if line2.debit > 0:
                                line2.account_id = self._get_tax_account(tax)
                                
                        
                        payment.action_post()

                        tax_payment = payment

                        if len(tax_payment) > 0:
                            for move in self.line_ids.filtered(lambda x: x.move_id.move_type != 'entry' and x.move_id.id == line.invoice_id.id):
                                move.move_id.write({'retention_payment':[(6,0,tax_payment.ids)]})
                                
        res = super(PaymentRegister, self)._create_payments()

        for pay in res:
            pay.write({'numero_de_libramiento':self.numero_de_libramiento})

        return res



class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_request_id = fields.Many2one(
        'custom.warehouse.stock.request',
        string="Warehouse Stock Request",
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    @api.onchange('picking_type_id', 'partner_id')
    def _onchange_picking_type(self):
        ctx = self._context.copy()
        if not ctx.get('is_warehouse_stock_request'):
            return super(StockPicking, self)._onchange_picking_type()
        # if self.picking_type_id and self.state == 'draft' and not ctx.get('is_warehouse_stock_request'):
        #     self = self.with_company(self.company_id)
        #     if self.picking_type_id.default_location_src_id:
        #         location_id = self.picking_type_id.default_location_src_id.id
        #     elif self.partner_id:
        #         location_id = self.partner_id.property_stock_supplier.id
        #     else:
        #         customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

        #     if self.picking_type_id.default_location_dest_id:
        #         location_dest_id = self.picking_type_id.default_location_dest_id.id
        #     elif self.partner_id:
        #         location_dest_id = self.partner_id.property_stock_customer.id
        #     else:
        #         location_dest_id, supplierloc = self.env['stock.warehouse']._get_partner_locations()

        #     self.location_id = location_id
        #     self.location_dest_id = location_dest_id
        #     (self.move_lines | self.move_ids_without_package).update({
        #         "picking_type_id": self.picking_type_id,
        #         "company_id": self.company_id,
        #     })

        if self.partner_id and self.partner_id.picking_warn:
            if self.partner_id.picking_warn == 'no-message' and self.partner_id.parent_id:
                partner = self.partner_id.parent_id
            elif self.partner_id.picking_warn not in ('no-message', 'block') and self.partner_id.parent_id.picking_warn == 'block':
                partner = self.partner_id.parent_id
            else:
                partner = self.partner_id
            if partner.picking_warn != 'no-message':
                if partner.picking_warn == 'block':
                    self.partner_id = False
                return {'warning': {
                    'title': ("Warning for %s") % partner.name,
                    'message': partner.picking_warn_msg
                }}