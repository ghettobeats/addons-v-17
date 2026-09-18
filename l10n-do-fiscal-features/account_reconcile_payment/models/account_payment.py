#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class AccountRegisterPaymentsInvoice(models.TransientModel):
    _name = "account.register.payments.invoice"
    _description = "Account Register Payments Invoice"

    def _get_tax_ids_domain(self):
        domain = [("invoice_repartition_line_ids", "!=", False), ("amount", "<", 0)]
        ctx = self.env.context
        if "active_model" in ctx and ctx["active_model"] == "account.move":
            invoice = self.env["account.move"].browse(ctx.get("active_ids", []))
            if invoice and invoice[0].move_type in ("in_invoice", "out_invoice"):
                tax_type = (
                    "sale" if invoice[0].move_type == "out_invoice" else "purchase"
                )
                domain.append(("type_tax_use", "=", tax_type))
        return domain

    reconcile_register_id = fields.Many2one(
        "account.payment.register",
        string="Register Payment Wizard",
    )
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    reference = fields.Char(related="invoice_id.l10n_do_fiscal_number")
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        domain=lambda self: self._get_tax_ids_domain(),
    )
    residual = fields.Monetary(related="invoice_id.amount_residual")
    currency_id = fields.Many2one(related="invoice_id.currency_id")
    amount = fields.Float(
        compute="_compute_amount",
        help="Amount to be applied from new payment to this invoice",
    )

    @api.depends("residual", "invoice_id", "tax_ids")
    def _compute_amount(self):
        for invoice_line in self:
            tax_amount = 0
            for line in invoice_line.invoice_id.invoice_line_ids:
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
                        % invoice_line.invoice_id.number
                    )
                )

            if len(invoice_line.tax_ids.mapped("tax_group_id")) < len(
                invoice_line.tax_ids
            ):
                raise UserError(
                    _(
                        "Cannot apply multiple taxes of same group in "
                        "invoice %s" % invoice_line.invoice_id.number
                    )
                )


class PaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    l10n_do_payments_invoice_ids = fields.One2many(
        "account.register.payments.invoice",
        "reconcile_register_id",
        string="Reconciled taxes",
    )

    l10n_do_reconcile_taxes = fields.Boolean()

    def _get_reconciled_payment_move_journal(self):
        journal_id = self.env["account.journal"].search(
            [
                ("l10n_do_reconciled_payments_journal", "=", True),
                ("company_id", "=", self.journal_id.company_id.id),
            ],
            limit=1,
        )
        if not journal_id:
            raise ValidationError(
                _("No Miscellaneous journal found to perform this " "payment")
            )
        return journal_id.id

    def _get_move_amounts(self, line, tax):

        invoice_id = line.invoice_id
        amount = invoice_id.amount_untaxed_signed * (abs(tax.amount) / 100)
        aml_obj = self.env["account.move.line"]

        aml_vals = aml_obj._get_fields_onchange_subtotal_model(
            amount,
            invoice_id.move_type,
            invoice_id.currency_id,
            invoice_id.company_id,
            self.payment_date,
        )

        return aml_vals["debit"], aml_vals["credit"], aml_vals["amount_currency"]

    @api.model
    def _get_tax_account(self, tax):
        accounts = []
        for line in tax.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ):
            accounts.append(line.account_id)
        return accounts[0].id if accounts else []

    @api.model
    def _get_invoice_reconcile_move_account(self, invoice):
        """
        Returns invoice account depending on invoice type:
        out_invoice: debit aml account
        in_invoice: credit aml account
        """

        if invoice.move_type not in ("out_invoice", "in_invoice"):
            raise ValidationError(
                _("Only Customer Invoice and Vendor Bill apply to reconcile payments")
            )
        aml_field = "credit" if invoice.move_type == "in_invoice" else "debit"
        account = invoice.line_ids.filtered(lambda l: getattr(l, aml_field) > 0)[
            0
        ].mapped("account_id")
        return account[0].id if account else False

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

    def _compute_payment_amount(self):
        self.ensure_one()

        l10n_do_payments_invoice_ids = self.l10n_do_payments_invoice_ids
        if not l10n_do_payments_invoice_ids:
            l10n_do_payments_invoice_ids = self.l10n_do_payments_invoice_ids.browse(
                self.env.context.get("invoices", [])
            )

        invoice_ids = l10n_do_payments_invoice_ids.mapped("invoice_id")

        payment_currency = (
            self.currency_id
            or self.journal_id.currency_id
            or self.journal_id.company_id.currency_id
            or invoice_ids
            and invoice_ids[0].currency_id
        )

        total = 0
        for inv in l10n_do_payments_invoice_ids:
            if inv.currency_id == payment_currency:
                total += inv.amount * -1
            else:
                amount_residual = invoice_ids[0].currency_id._convert(
                    inv.amount,
                    payment_currency,
                    inv.invoice_id.company_id,
                    self.payment_date,
                )
                total += amount_residual * -1
        return abs(total)

    @api.depends(
        "source_amount",
        "source_amount_currency",
        "source_currency_id",
        "company_id",
        "currency_id",
        "payment_date",
    )
    def _compute_amount(self):
        l10n_do_reconcile_taxes_wizard = self.filtered(lambda w: w.l10n_do_reconcile_taxes)
        for wizard in l10n_do_reconcile_taxes_wizard:
            wizard.amount = self.with_context(
                l10n_do_reconcile_taxes=True,
                invoices=[i.id for i in self.l10n_do_payments_invoice_ids],
            )._compute_payment_amount()

        super(PaymentRegister, self - l10n_do_reconcile_taxes_wizard)._compute_amount()

    @api.onchange("l10n_do_reconcile_taxes", "l10n_do_payments_invoice_ids")
    def _onchange_l10n_do_payments_invoice_ids(self):

        invoices = self._context.get("active_ids")

        if self.l10n_do_reconcile_taxes and invoices and not self.l10n_do_payments_invoice_ids:
            invoice_ids = self.env["account.move"].browse(invoices)
            self.l10n_do_payments_invoice_ids = [
                (0, 0, {"invoice_id": inv.id, "amount": inv.amount_residual})
                for inv in invoice_ids
            ]
        elif self.l10n_do_reconcile_taxes and invoices and self.l10n_do_payments_invoice_ids:
            self._compute_from_lines()  # update payment amount
        else:
            self.l10n_do_payments_invoice_ids = [(5, 0, 0)]

    @api.onchange("l10n_do_reconcile_taxes")
    def onchange_l10n_do_reconcile_taxes(self):
        self.group_payment = self.l10n_do_reconcile_taxes

    def _create_payments(self):

        if self.l10n_do_reconcile_taxes:
            if (
                len(
                    set(
                        self.l10n_do_payments_invoice_ids.mapped("invoice_id").mapped(
                            "commercial_partner_id"
                        )
                    )
                )
                > 1
            ):
                raise UserError(_("Cannot reconcile taxes when multiple partners"))

            if not self.l10n_do_payments_invoice_ids:
                return {"type": "ir.actions.act_window_close"}

            invoices = self.env.context.get("active_ids", [])
            invoice_ids = self.env["account.move"].browse(invoices)
            amount = self.with_context(
                l10n_do_reconcile_taxes=True,
                invoices=[i.id for i in self.l10n_do_payments_invoice_ids],
            )._compute_payment_amount()

            # Payment currency amount
            payment_amount = self.journal_id.currency_id._convert(
                amount,
                invoice_ids[0].currency_id,
                invoice_ids[0].company_id,
                self.payment_date,
            )

            if abs(payment_amount) < float_round(
                sum([i.amount for i in self.l10n_do_payments_invoice_ids]),
                precision_rounding=0.01,
            ):
                raise UserError(
                    _(
                        "Error. This payment method require all invoices "
                        "total to be paid"
                    )
                )

        if self.l10n_do_reconcile_taxes:
            invoices = self.l10n_do_payments_invoice_ids.mapped("invoice_id")

            # Reconcile taxes move lines
            for inv, amls in self._create_reconciled_taxes_move(invoices).items():
                for ml in amls:
                    inv.js_assign_outstanding_line(ml)

        return super(PaymentRegister, self)._create_payments()
