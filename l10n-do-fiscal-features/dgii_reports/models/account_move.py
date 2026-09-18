# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class InvoiceServiceTypeDetail(models.Model):
    _name = "invoice.service.type.detail"
    _description = "Invoice Service Type Detail"

    name = fields.Char()
    code = fields.Char(size=2)
    parent_code = fields.Char()

    _sql_constraints = [
        ("code_unique", "unique(code)", _("Code must be unique")),
    ]


class AccountMove(models.Model):
    _inherit = "account.move"

    # ISR Percibido       --> Este campo se va con 12 espacios en 0 para el 606
    # ITBIS Percibido     --> Este campo se va con 12 espacios en 0 para el 606
    l10n_do_payment_date = fields.Date(compute="_compute_dgii_fields", store=True)
    l10n_do_service_total_amount = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_good_total_amount = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_invoiced_itbis = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_withholded_itbis = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_proportionality_tax = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_cost_itbis = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_advance_itbis = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_isr_withholding_type = fields.Char(
        compute="_compute_dgii_fields", store=True, size=2
    )
    l10n_do_income_withholding = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_selective_tax = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_other_taxes = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_legal_tip = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_payment_form = fields.Selection(
        [
            ("01", "Cash"),
            ("02", "Check / Transfer / Deposit"),
            ("03", "Credit Card / Debit Card"),
            ("04", "Credit"),
            ("05", "Swap"),
            ("06", "Credit Note"),
            ("07", "Mixed"),
        ],
        compute="_compute_dgii_fields",
        store=True,
    )
    l10n_do_third_withheld_itbis = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_third_income_withholding = fields.Monetary(
        compute="_compute_dgii_fields",
        store=True,
        currency_field="company_currency_id",
    )
    l10n_do_is_exterior = fields.Boolean(
        compute="_compute_dgii_l10n_do_is_exterior", store=True
    )
    l10n_do_service_type = fields.Selection(
        [
            ("01", "Gastos de Personal"),
            ("02", "Gastos por Trabajos, Suministros y Servicios"),
            ("03", "Arrendamientos"),
            ("04", "Gastos de Activos Fijos"),
            ("05", "Gastos de Representación"),
            ("06", "Gastos Financieros"),
            ("07", "Gastos de Seguros"),
            ("08", "Gastos por Regalías y otros Intangibles"),
        ],
        string="Service Type",
    )
    l10n_do_service_type_detail = fields.Many2one(
        "invoice.service.type.detail",
        string="Service Type Detail",
    )
    l10n_do_available_service_type_detail = fields.Many2many(
        "invoice.service.type.detail",
        string="Available Service Type Detail",
        compute="_compute_available_service_type_detail",
    )
    l10n_do_fiscal_status = fields.Selection(
        [("normal", "Partial"), ("done", "Reported"), ("blocked", "Not Sent")],
        string="Fiscal Status",
        copy=False,
        help="* The 'Grey' status means invoice isn't fully reported and may appear "
        "in other report if a withholding is applied.\n"
        "* The 'Green' status means invoice is fully reported.\n"
        "* The 'Red' status means invoice is included in a non sent DGII report.\n"
        "* The blank status means that the invoice have"
        "not been included in a report.",
    )

    @api.constrains("invoice_line_ids")
    def _check_isr_tax(self):
        """Restrict one ISR tax per invoice"""
        for inv in self.filtered(
            lambda i: i.l10n_latam_use_documents and i.country_code == "DO"
        ):
            line_tax_ids = inv.mapped("invoice_line_ids").mapped("tax_ids")
            line = [
                tax.tax_group_id.name
                for tax in line_tax_ids
                if tax.tax_group_id.name in ["ISR", "ITBIS"]
            ]
            if len(line) != len(set(line)):
                raise ValidationError(
                    _("An invoice cannot have multiple" "withholding taxes.")
                )

    @api.constrains(
        "state", "line_ids", "l10n_latam_document_type_id", "company_id", "move_type"
    )
    def _check_special_exempt(self):
        """Validates that an invoice with a Special Tax Payer type does not contain
        nor ITBIS or ISC.
        See DGII Norma 05-19, Art 3 for further information.
        """
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id
            and r.move_type == "out_invoice"
            and r.state in ("draft", "cancel")
        ):
            # TODO: include Gasto Menor in this constrain
            if rec.l10n_latam_document_type_id.l10n_do_ncf_type[-7:] == "special":
                # If any invoice tax in ITBIS or ISC
                taxes = ("ITBIS", "ISC")
                if any(
                    [
                        tax
                        for tax in rec.line_ids.filtered("tax_line_id").filtered(
                            lambda tax: tax.tax_group_id.name in taxes
                            and tax.tax_base_amount != 0
                        )
                    ]
                ):
                    raise UserError(
                        _(
                            "You cannot validate and invoice of Fiscal Type "
                            "Regímen Especial with ITBIS/ISC.\n\n"
                            "See DGII General Norm 05-19, Art. 3 for further "
                            "information"
                        )
                    )

    @api.constrains("state", "company_id", "move_type", "amount_untaxed_signed")
    def _check_invoice_amount(self):
        """Validates that an invoices has an amount greater than 0."""
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.company_id
            and r.move_type == "out_invoice"
            and r.state != "draft"
        ):
            if rec.amount_untaxed_signed == 0:
                raise UserError(
                    _("You cannot validate an invoice with a total amount equals to 0.")
                )

    @api.constrains(
        "state",
        "line_ids",
        "partner_id",
        "company_id",
        "move_type",
        "l10n_latam_document_type_id",
    )
    def _check_products_export_ncf(self):
        """Validates that an invoices with a partner from country != DO
        and products type != service must have Exportaciones NCF.
        See DGII Norma 05-19, Art 10 for further information.
        """
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id
            and r.move_type == "out_invoice"
            and r.state in ("posted", "cancel")
            and r.commercial_partner_id.country_id
            and r.commercial_partner_id.country_id.code != "DO"
            and r.commercial_partner_id.l10n_do_dgii_tax_payer_type == "foreigner"
        ):
            if any(
                [
                    p
                    for p in rec.invoice_line_ids.mapped("product_id")
                    if p.type != "service"
                ]
            ):
                if rec.l10n_latam_document_type_id.l10n_do_ncf_type[-6:] != "export":
                    raise UserError(
                        _(
                            "Goods sales to overseas customers must have "
                            "Exportaciones Fiscal Type"
                        )
                    )
            elif rec.l10n_latam_document_type_id.l10n_do_ncf_type[-8:] != "consumer":
                raise UserError(
                    _(
                        "Services sales to overseas customer must have "
                        "Consumo Fiscal Type"
                    )
                )

    @api.constrains(
        "state", "line_ids", "company_id", "l10n_latam_document_type_id", "move_type"
    )
    def _check_informal_withholding(self):
        """Validates an invoice with Comprobante de Compras has 100% ITBIS
        withholding.
        See DGII Norma 05-19, Art 7 for further information.
        """
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id
            and r.l10n_latam_document_type_id.l10n_do_ncf_type
            and r.move_type == "in_invoice"
            and r.state == "draft"
        ):

            if rec.l10n_latam_document_type_id.l10n_do_ncf_type[-8:] == "informal":
                # If the sum of all taxes of category ITBIS is not 0
                if sum(
                    [
                        tax.amount
                        for tax in rec.line_ids.tax_ids.filtered(
                            lambda tax: tax.tax_group_id.name == "ITBIS"
                        )
                    ]
                ):
                    raise UserError(_("You must withhold 100% of ITBIS"))

    @api.constrains("state", "partner_id", "l10n_latam_document_number")
    def _check_fiscal_purchase(self):
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id.l10n_do_ncf_type is not False
            and r.move_type == "in_invoice"
            and r.l10n_latam_document_number
        ):
            l10n_latam_document_number = rec.l10n_latam_document_number
            l10n_latam_document_type = rec.l10n_latam_document_type_id.l10n_do_ncf_type

            if l10n_latam_document_number and l10n_latam_document_type[-6:] == "fiscal":
                if l10n_latam_document_number[1:3] in ("02", "32"):
                    raise ValidationError(
                        _(
                            "NCF *{}* does not correspond with the fiscal type\n\n"
                            "You cannot register Consumo NCF (02/32) for purchases"
                        ).format(l10n_latam_document_number)
                    )

    @api.onchange("journal_id")
    def ext_onchange_journal_id(self):
        self.l10n_do_service_type = False
        self.l10n_do_service_type_detail = False

    def _get_invoice_taxes_vals(self):
        vals = {}
        for aml_id in self.line_ids.filtered(
            lambda line: not line.product_id and line.tax_line_id
        ):
            tax = aml_id.tax_line_id
            vals[tax] = {
                "tax_group_id": tax.tax_group_id,
                "amount": sum([(aml.credit + aml.debit) for aml in aml_id]),
                "account_id": aml_id.account_id,
            }

        return vals

    def _get_payment_string(self):
        """Compute Vendor Bills payment method string

        Keyword / Values:
        cash        -- Efectivo
        bank        -- Cheques / Transferencias / Depósitos
        card        -- Tarjeta Crédito / Débito
        credit      -- Compra a Crédito
        swap        -- Permuta
        credit_note -- Notas de Crédito
        mixed       -- Mixto
        """
        payments = []
        p_string = ""

        for payment in self._get_reconciled_info_JSON_values():
            payment_id = self.env["account.payment"].browse(
                payment.get("account_payment_id")
            )
            move_id = False
            if payment_id:
                if payment_id.journal_id.type in ["cash", "bank"]:
                    p_string = payment_id.journal_id.l10n_do_payment_form

            if not payment_id:
                move_id = self.env["account.move"].browse(payment.get("move_id"))
                if move_id:
                    p_string = "swap"

            # If invoice is paid, but the payment doesn't come from
            # a journal, assume it is a credit note
            payment = p_string if payment_id or move_id else "credit_note"
            payments.append(payment)

        methods = {p for p in payments}
        if len(methods) == 1:
            return list(methods)[0]
        elif len(methods) > 1:
            return "mixed"

    def _get_dgii_l10n_do_payment_date(self):

        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.move_type in ("in_invoice", "out_invoice")
            and any(
                [
                    self.l10n_do_withholded_itbis,
                    self.l10n_do_income_withholding,
                    self.l10n_do_third_withheld_itbis,
                    self.l10n_do_third_income_withholding,
                ]
            )
        ):
            try:
                max_date = max(
                    [
                        payment["date"]
                        for payment in self._get_reconciled_info_JSON_values()
                    ]
                )
            except ValueError:
                return False

            date_invoice = self.invoice_date
            return max_date if max_date >= date_invoice else date_invoice

        return False

    def _get_dgii_service_good_amount(self):
        service_amount = 0
        good_amount = 0
        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.move_type in ["in_invoice", "in_refund"]
            and self.state != "draft"
        ):
            service_amount = sum(
                [
                    sum([line.debit, line.credit])
                    for line in self.invoice_line_ids.filtered(
                        lambda l: not l.product_id
                        or l.product_id.type not in ["product", "consu"]
                    )
                ]
            )
            good_amount = sum(
                [
                    sum([line.debit, line.credit])
                    for line in self.invoice_line_ids.filtered(
                        lambda l: l.product_id.type in ["product", "consu"]
                    )
                ]
            )

        return service_amount, good_amount

    def _get_dgii_l10n_do_invoiced_itbis(self):
        amount = 0
        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.state != "draft"
        ):
            itbis_taxes = ["ITBIS", "ITBIS 18%"]
            for tax, vals in self._get_invoice_taxes_vals().items():
                if tax["tax_group_id"].name in itbis_taxes and tax.amount > 0:
                    amount += vals["amount"]

        return amount

    def _get_counterpart_aml(self, aml):
        """
        Ugly as fuck. It may fail, sometimes. But is the way to find a
        counterpart account move line until a better way is found.
        """
        # TODO: implement a better workaround
        aml_id = aml.search(
            [
                ("move_id", "=", aml.move_id.id),
                ("credit", "=", aml.debit),
                ("debit", "=", aml.credit),
            ],
            limit=1,
        )
        return aml_id

    def _get_dgii_withheld_taxes(self):
        third_wh_itbis = 0
        third_income_wh = 0
        wh_itbis = 0
        income_wh = 0

        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.payment_state != "not_paid"
            and self.move_type
            in (
                "out_invoice",
                "in_invoice",
            )
        ):

            withholding_amounts_dict = {"A34": 0, "A36": 0, "ISR": 0, "A38": 0}

            inv_payment_vals = [
                payment_data for payment_data in self._get_reconciled_info_JSON_values()
            ]
            payment_data = []
            for payment_vals in inv_payment_vals:
                move_line = self.env["account.move.line"].browse(
                    payment_vals["payment_id"]
                )
                if payment_vals["account_payment_id"]:
                    move_id = move_line.move_id
                    amls = move_id.line_ids.filtered(
                        lambda ml: ml.account_id.l10n_do_account_fiscal_type
                        in withholding_amounts_dict
                    )
                    payment_data.extend(
                        [
                            {
                                "account_id": aml.account_id,
                                "amount": sum([aml.credit, aml.debit]),
                            }
                            for aml in amls
                        ]
                    )
                else:
                    counterpart_move_line = self._get_counterpart_aml(move_line)
                    payment_data.append(
                        {
                            "account_id": counterpart_move_line.account_id,
                            "amount": sum(
                                [
                                    counterpart_move_line.credit,
                                    counterpart_move_line.debit,
                                ]
                            ),
                        }
                    )
            for payment in payment_data:

                account = payment["account_id"]
                if not account or account.user_type_id.type in (
                    "receivable",
                    "payable",
                ):
                    continue

                fiscal_type = account.l10n_do_account_fiscal_type
                if not fiscal_type:
                    continue

                if fiscal_type in withholding_amounts_dict:
                    withholding_amounts_dict[
                        account.l10n_do_account_fiscal_type
                    ] += payment["amount"]
                else:
                    raise UserError(
                        _(
                            "%s account has a wrong Fiscal Type. Only the following "
                            "Fiscal Types are allowed for withholding: "
                            "(A34, A36, A38, ISR)"
                        )
                        % account.name
                    )

            aml_ids = self.line_ids.filtered(
                lambda aml: aml.account_id.l10n_do_account_fiscal_type
                in withholding_amounts_dict
            )

            for aml in aml_ids:
                withholding_amounts_dict[
                    aml.account_id.l10n_do_account_fiscal_type
                ] += sum([aml.debit, aml.credit])

            withheld_itbis = sum(
                v for k, v in withholding_amounts_dict.items() if k in ("A34", "A36")
            )
            withheld_isr = sum(
                v for k, v in withholding_amounts_dict.items() if k in ("ISR", "A38")
            )

            if self.move_type == "out_invoice":
                third_wh_itbis = withheld_itbis
                third_income_wh = withheld_isr

            else:
                wh_itbis = withheld_itbis
                income_wh = withheld_isr

        return third_wh_itbis, third_income_wh, wh_itbis, income_wh

    def _get_dgii_taxes_fields(self):
        selective_tax = 0
        other_taxes = 0
        legal_tip = 0
        proportionality_tax = 0
        cost_itbis = 0

        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.state != "draft"
        ):
            tax_vals = self._get_invoice_taxes_vals()
            # Monto Impuesto Selectivo al Consumo
            selective_tax = sum(
                [
                    v["amount"]
                    for k, v in tax_vals.items()
                    if v["tax_group_id"].name == "ISC"
                ]
            )

            # Monto Otros Impuestos/Tasas
            other_taxes = sum(
                [
                    v["amount"]
                    for k, v in tax_vals.items()
                    if v["tax_group_id"].name == "Otros Impuestos"
                ]
            )

            # Monto Propina Legal
            legal_tip = sum(
                [
                    v["amount"]
                    for k, v in tax_vals.items()
                    if v["tax_group_id"].name == "Propina"
                ]
            )

            # ITBIS sujeto a proporcionalidad
            proportionality_tax = sum(
                [
                    v["amount"]
                    for k, v in tax_vals.items()
                    if v["account_id"].l10n_do_account_fiscal_type in ["A29", "A30"]
                ]
            )

            # ITBIS llevado al Costo
            cost_itbis = sum(
                [
                    v["amount"]
                    for k, v in tax_vals.items()
                    if v["account_id"].l10n_do_account_fiscal_type == "A51"
                ]
            )

        return selective_tax, other_taxes, legal_tip, proportionality_tax, cost_itbis

    def _get_dgii_l10n_do_isr_withholding_type(self):
        """Compute ISR Withholding Type

        Keyword / Values:
        01 -- Alquileres
        02 -- Honorarios por Servicios
        03 -- Otras Rentas
        04 -- Rentas Presuntas
        05 -- Intereses Pagados a Personas Jurídicas
        06 -- Intereses Pagados a Personas Físicas
        07 -- Retención por Proveedores del Estado
        08 -- Juegos Telefónicos
        """

        isr_withholding_type = False
        if (
            self.l10n_latam_use_documents
            and self.country_code == "DO"
            and self.move_type == "in_invoice"
            and self.payment_state != "not_paid"
        ):

            line_id = self.line_ids.filtered(
                lambda aml: aml.account_id.l10n_do_account_fiscal_type == "ISR"
            )
            if line_id:  # invoice tax lines use case
                isr_withholding_type = line_id[0].account_id.l10n_do_isr_retention_type
            else:  # in payment/journal entry use case
                aml_ids = (
                    self.browse(
                        p["move_id"] for p in self._get_reconciled_info_JSON_values()
                    )
                    .mapped("line_ids")
                    .filtered(lambda aml: aml.account_id.l10n_do_isr_retention_type)
                )
                if aml_ids:
                    isr_withholding_type = aml_ids[0].account_id.isr_retention_type

        return isr_withholding_type

    def _get_dgii_invoice_l10n_do_payment_form(self):

        if self.l10n_latam_use_documents and self.country_code == "DO":
            if self.payment_state != "not_paid":
                payment_dict = {
                    "cash": "01",
                    "bank": "02",
                    "card": "03",
                    "credit": "04",
                    "swap": "05",
                    "credit_note": "06",
                    "mixed": "07",
                }
                return payment_dict.get(self._get_payment_string())

            return "04"

        return False

    def _get_signed_data(self, data):
        sign_map = {
            "out_invoice": 1,
            "out_refund": -1,
            "in_invoice": -1,
            "in_refund": 1,
            "entry": 1,
        }
        for field, value in data.items():
            data[field] = sign_map[self.move_type] * value

        return data

    @api.depends("l10n_latam_document_type_id.doc_code_prefix")
    def _compute_dgii_l10n_do_is_exterior(self):
        l10n_do_invoice = self.filtered(
            lambda i: i.l10n_latam_use_documents and i.country_code == "DO"
        )
        for inv in l10n_do_invoice:
            inv.l10n_do_is_exterior = (
                inv.l10n_latam_document_type_id.doc_code_prefix
                in (
                    "B17",
                    "E47",
                )
            )
        (self - l10n_do_invoice).l10n_do_is_exterior = False

    @api.depends(
        "move_type",
        "state",
        "invoice_date",
        "line_ids.debit",
        "line_ids.credit",
        "invoice_line_ids",
        "line_ids.account_id",
        "payment_state",
        "invoice_line_ids.tax_ids",
        "invoice_line_ids.product_id",
    )
    def _compute_dgii_fields(self):

        invoices = self.filtered(
            lambda inv: inv.l10n_latam_use_documents
            and inv.country_code == "DO"
            and inv.move_type not in ("entry", "out_receipt", "in_receipt")
        )

        for invoice in invoices:
            service_total, good_total = invoice._get_dgii_service_good_amount()
            (
                third_wh_itbis,
                third_income_wh,
                wh_itbis,
                income_wh,
            ) = invoice._get_dgii_withheld_taxes()

            (
                selective_tax,
                other_taxes,
                legal_tip,
                proportionality_tax,
                cost_itbis,
            ) = invoice._get_dgii_taxes_fields()

            invoiced_itbis = invoice._get_dgii_l10n_do_invoiced_itbis()
            advance_itbis = invoiced_itbis - cost_itbis

            new_vals = {
                "l10n_do_isr_withholding_type": invoice._get_dgii_l10n_do_isr_withholding_type(),
                "l10n_do_payment_form": invoice._get_dgii_invoice_l10n_do_payment_form(),
            }

            new_vals.update(
                invoice._get_signed_data(
                    {
                        "l10n_do_service_total_amount": service_total,
                        "l10n_do_good_total_amount": good_total,
                        "l10n_do_invoiced_itbis": invoiced_itbis,
                        "l10n_do_withholded_itbis": wh_itbis,
                        "l10n_do_income_withholding": income_wh,
                        "l10n_do_third_withheld_itbis": third_wh_itbis,
                        "l10n_do_third_income_withholding": third_income_wh,
                        "l10n_do_selective_tax": selective_tax,
                        "l10n_do_other_taxes": other_taxes,
                        "l10n_do_legal_tip": legal_tip,
                        "l10n_do_proportionality_tax": proportionality_tax,
                        "l10n_do_cost_itbis": cost_itbis,
                        "l10n_do_advance_itbis": advance_itbis,
                    }
                )
            )

            invoice.write(new_vals)

            # We calc this field after because it needs to check first if
            # invoice has any withholding
            invoice.l10n_do_payment_date = invoice._get_dgii_l10n_do_payment_date()

    @api.depends("l10n_do_service_type")
    def _compute_available_service_type_detail(self):
        self.l10n_do_service_type_detail = False
        for move in self:
            move.l10n_do_available_service_type_detail = (
                move.l10n_do_available_service_type_detail.search(
                    [("parent_code", "=", move.l10n_do_service_type)]
                )
            )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains("tax_ids")
    def _check_line_unique_itbis(self):
        """Check there is only one ITBIS tax per line"""
        for inv_line in self.filtered(
            lambda line: line.tax_ids
            and line.move_id.l10n_latam_use_documents
            and line.move_id.country_code == "DO"
        ):
            line_tax_ids = inv_line.tax_ids.filtered(
                lambda tax: tax.tax_group_id.name == "ITBIS" and tax.amount >= 0
            )
            if line_tax_ids and len(line_tax_ids) > 1:
                raise UserError(
                    _("An invoice cannot have multiple ITBIS taxes per line.")
                )
