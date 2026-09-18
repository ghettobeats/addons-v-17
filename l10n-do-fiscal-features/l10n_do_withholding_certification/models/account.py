#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

import base64
from num2words import num2words

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    _inherit = "account.account"

    is_l10n_do_withholding_account = fields.Boolean()
    l10n_do_legal_base = fields.Char(
        help="Article, norm or whatever legal statement that enforce this "
        "withholding to be applied.",
    )
    l10n_do_tax_name = fields.Char()


class AccountPayment(models.Model):
    _inherit = "account.payment"

    has_l10n_do_withholding = fields.Boolean(
        compute="_compute_has_l10n_do_withholding",
        store=True,
        copy=False,
    )
    l10n_do_withholding_type = fields.Selection(
        [("payment", "Payment"), ("tax", "Invoice tax"), ("entry", "Journal Entry")],
        compute="_compute_has_l10n_do_withholding",
        store=True,
        copy=False,
    )

    @api.depends(
        "state",
        "payment_type",
        "line_ids.full_reconcile_id",
    )
    def _compute_has_l10n_do_withholding(self):
        for payment in self:
            if payment.company_id.country_id.code == "DO" and payment.state not in (
                "draft",
                "cancel",
            ):

                # Payment journal entry withholding
                payment.has_l10n_do_withholding = any(
                    [
                        move_line.account_id.is_l10n_do_withholding_account
                        for move_line in payment.line_ids
                    ]
                )
                if payment.has_l10n_do_withholding:
                    payment.l10n_do_withholding_type = "payment"

                # Invoice line tax withholding
                reconciled_bill_ids = payment.reconciled_bill_ids
                if payment.is_matched:
                    reconciled_bill_ids += payment.reconciled_invoice_ids
                tax_line_ids = reconciled_bill_ids.mapped("invoice_line_ids").mapped(
                    "tax_ids"
                )
                rep_line_ids = tax_line_ids.mapped("invoice_repartition_line_ids")
                if any(
                    [
                        rep_line.account_id.is_l10n_do_withholding_account
                        for rep_line in rep_line_ids
                    ]
                ):
                    payment.l10n_do_withholding_type = (
                        payment.l10n_do_withholding_type + "_tax"
                        if payment.l10n_do_withholding_type
                        and payment.l10n_do_withholding_type != "tax"
                        else "tax"
                    )
                    rep_line_ids = tax_line_ids.mapped("invoice_repartition_line_ids")
                    payment.has_l10n_do_withholding = any(
                        [
                            rep_line.account_id.is_l10n_do_withholding_account
                            for rep_line in rep_line_ids
                        ]
                    )

                    if payment.has_l10n_do_withholding:
                        payment.l10n_do_withholding_type = "tax"

                # Random journal entry
                if payment.is_reconciled and payment.l10n_do_withholding_type not in (
                    "payment",
                    "tax",
                ):

                    full_reconcile_id = payment.line_ids.mapped("full_reconcile_id")
                    if full_reconcile_id:
                        aml_ids = full_reconcile_id[0].reconciled_line_ids.filtered(
                            lambda aml: aml.journal_id.type not in ("sale", "purchase")
                        )
                        payment.has_l10n_do_withholding = any(
                            [
                                line.account_id.is_l10n_do_withholding_account
                                for line in aml_ids.mapped("move_id").mapped("line_ids")
                            ]
                        )
                        if payment.has_l10n_do_withholding:
                            payment.l10n_do_withholding_type = "entry"
            else:
                payment.l10n_do_withholding_type = False
                payment.has_l10n_do_withholding = False

    def _post_printing_message(self, report_template):
        attach = self.env["ir.attachment"].create(
            {
                "name": _("%s Withholding Cert" % self.name),
                "store_fname": "WHCERT",
                "datas": self._get_rendered_report(report_template),
                "res_model": "account.payment",
                "res_id": self.id,
            }
        )

        self.message_post(
            body=_("New Withholding Certification printed"), attachment_ids=[attach.id]
        )

    def _get_rendered_report(self, report_template):
        if report_template.report_type in ["qweb-html", "qweb-pdf"]:
            result, report_format = report_template._render_qweb_pdf([self.id])
        else:
            res = report_template.render([self.id])
            if not res:
                raise UserError(
                    _("Unsupported report type %s found.") % report_template.report_type
                )
            result, format = res

        return base64.b64encode(result)

    def withholding_print(self):
        self.ensure_one()

        l10n_do_withholding_cert_type = (
            self.env.user.company_id.l10n_do_withholding_cert_type
        )

        if not l10n_do_withholding_cert_type:
            raise ValidationError(
                _(
                    "No Withholding Certification Type found. "
                    "Select one in company settings."
                )
            )

        report_template = self.env.ref(
            "l10n_do_withholding_certification.l10n_do_withholding_cert"
        )

        self._post_printing_message(report_template)

        return report_template.report_action(self)

    def get_amount_in_words(self, amount, is_money=True):
        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang="en").title()

        formatted = "%.{0}f".format(self.currency_id.decimal_places) % amount
        parts = formatted.partition(".")
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang = (
            self.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "es_DO")])
        )

        amt_value = _num2words(integer_value, lang=lang.iso_code)
        amount_words = tools.ustr(str(amt_value))
        if is_money:
            amount_words += " " + self.currency_id.currency_unit_label
            amount_words += " " + "con " + str(fractional_value) + "/100"

        return amount_words

    def get_date_string(self, date, short_date=False):

        month_map = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre",
        }

        day = date.day
        month = month_map[date.month]
        year = date.year

        if not short_date:
            long_date = (
                self.get_amount_in_words(day, is_money=False),
                day,
                month,
                self.get_amount_in_words(year, is_money=False),
                year,
            )
            return "%s (%s) días del mes de %s del año %s (%s)" % long_date
        else:
            return "%s de %s %s" % (day, month, year)

    def _get_withholding_vals(self):

        return {
            "amount_in_words": "",
            "invoices_data": [],
            "payments_amount": 0,
            "paid_amount": 0,
            "withholding_values": {},
        }

    def _get_total_withheld(self, invoices_data):
        amount = 0
        for invoice in invoices_data:
            for withholding in invoice["withholding"]:
                amount += withholding["amount"]

        return amount

    def _get_invoice_reconciled_amount(self, payments_vals, multi=False):
        if not multi:
            payments_vals = [
                p for p in payments_vals if p.get("account_payment_id") == self.id
            ]
        else:
            payments_vals = [p for p in payments_vals if p["account_payment_id"]]

        return sum(
            [
                self.env["res.currency"]
                .search([("symbol", "=", p["currency"])], limit=1)
                ._convert(
                    p["amount"], self.company_id.currency_id, self.company_id, self.date
                )
                for p in payments_vals
            ]
        )

    @api.model
    def _get_invoice_withholding_data(self, payments_vals):
        Aml = self.env["account.move.line"]
        Payment = self.env["account.payment"]
        res = []
        for vals in payments_vals:
            if vals["account_payment_id"]:
                payment_id = Payment.browse(vals["account_payment_id"])
                for move_line in payment_id.line_ids.filtered(
                    lambda aml: aml.account_id.is_l10n_do_withholding_account
                ):
                    res.append(
                        {"account_id": move_line.account_id, "amount": move_line.credit}
                    )
            else:
                aml_id = Aml.browse(vals["payment_id"])
                res.append({"account_id": aml_id.account_id, "amount": aml_id.credit})

        return sorted(res, key=lambda d: d.keys())

    def get_l10n_do_legal_base_string(self, withholding_values):

        message = ""
        wh_len = len(list(withholding_values))
        for num, wh_vals in enumerate(list(withholding_values), 1):
            if 1 < wh_len == num:
                message += " y "
            message += wh_vals[0].l10n_do_legal_base or ""

        if wh_len > 1:
            message += ", respectivamente"

        return message

    def _get_withholding_values(self, wh_values, withholding_data):
        for vals in withholding_data:
            if vals["account_id"] not in wh_values:
                wh_values.update({vals["account_id"]: vals["amount"]})
            else:
                wh_values[vals["account_id"]] += vals["amount"]
        return wh_values

    def _get_counterpart_aml(self, aml):
        """
        Ugly as fuck. It may fail, sometimes. But is the way to find a
        counterpart account move line until a better way is found.
        """
        # TODO: implement a better workaround
        aml_id = self.env["account.move.line"].search(
            [("move_id", "=", aml.move_id.id), ("credit", "=", aml.debit)],
            limit=1,
        )
        return aml_id

    def _get_payment_withholding_data(self):
        """
        CASE 1: 1 payment / 1 invoice. Register Payment button
        In this case an invoice is paid from Register Payment button. An
        amount is subtracted from invoice total, mark it as fully paid
        and difference posted in a withholding account. Withholding
        amount is found in payment journal entry.
        """
        withholding_vals = self._get_withholding_vals()
        wh_values = {}
        for inv in self.reconciled_bill_ids:
            payments_vals = inv._get_reconciled_info_JSON_values()
            withholding_data = self._get_invoice_withholding_data(payments_vals)
            paid_amount = self._get_invoice_reconciled_amount(payments_vals)
            withholding_vals["invoices_data"].append(
                {
                    "date_invoice": inv.invoice_date,
                    "payment_id": self.id,
                    "invoice_id": inv.id,
                    "date": self.date,
                    "payment_amount": round(
                        self.amount + sum(wh["amount"] for wh in withholding_data), 2
                    ),
                    "reference": inv.l10n_do_fiscal_number,
                    "withholding": withholding_data,
                    "paid_amount": round(
                        paid_amount - sum(wh["amount"] for wh in withholding_data), 2
                    ),
                }
            )
            wh_values = self._get_withholding_values(wh_values, withholding_data)

        paid_amount = sum(aml.debit for aml in self.line_ids)
        withholding_vals["amount_in_words"] = self.get_amount_in_words(paid_amount)
        withholding_vals["paid_amount"] = paid_amount
        withholding_vals["payments_amount"] = paid_amount - self._get_total_withheld(
            withholding_vals["invoices_data"]
        )

        withholding_vals["withholding_values"] = wh_values

        return withholding_vals

    def _get_tax_withholding_data(self):
        """
        CASE 2: 1 payment / n invoices. Withholding tax in invoice lines
        One payment, one or more invoices. Withholding amount is found in
        invoice tax lines.

        CASE 3: n payments / 1 invoice. Withholding tax in invoice lines
        All invoice payment data is merged to one certification
        """

        withholding_vals = self._get_withholding_vals()
        wh_values = {}
        total_paid = 0
        reconciled_bill_ids = self.reconciled_bill_ids
        reconciled_bill_ids |= self.reconciled_invoice_ids
        for inv in reconciled_bill_ids:
            # at this point payment_vals should not contain credit notes nor
            # journal entries reconciled as payments, so we filter it
            payments_vals = [
                p
                for p in inv._get_reconciled_info_JSON_values()
                if p["account_payment_id"]
            ]

            withholding_data = [
                {
                    "account_id": ml.account_id,
                    "amount": abs(ml.credit),
                }
                for ml in inv.line_ids
                if (ml.credit and ml.account_id.is_l10n_do_withholding_account)
            ]

            paid_amount = self._get_invoice_reconciled_amount(payments_vals, multi=True)
            total_paid += paid_amount

            dates = [payment["date"] for payment in payments_vals]
            date = max(dates) if dates else False

            withholding_vals["invoices_data"].append(
                {
                    "date_invoice": inv.invoice_date,
                    "payment_id": self.id,
                    "invoice_id": inv.id,
                    "date": date,
                    "payment_amount": round(
                        paid_amount + sum(wh["amount"] for wh in withholding_data), 2
                    ),
                    "reference": inv.l10n_do_fiscal_number,
                    "withholding": withholding_data,
                    "paid_amount": paid_amount,
                }
            )
            wh_values = self._get_withholding_values(wh_values, withholding_data)

        total_paid_amount = total_paid + sum(
            [amount for x, amount in wh_values.items()]
        )
        withholding_vals["amount_in_words"] = self.get_amount_in_words(
            total_paid_amount
        )
        withholding_vals["paid_amount"] = total_paid_amount
        withholding_vals[
            "payments_amount"
        ] = total_paid_amount - self._get_total_withheld(
            withholding_vals["invoices_data"]
        )

        withholding_vals["withholding_values"] = wh_values

        return withholding_vals

    def _get_entry_withholding_data(self):
        """
        CASE 4: n payments / n invoices. Withholding in journal entry
        A journal entry is created containing a withholding move line and
        its counter part for each invoice in which a withholding is going
        to be applied. After that, withholding and payment are reconciled
        with each invoice.
        """
        withholding_vals = self._get_withholding_vals()
        wh_values = {}
        total_paid = 0
        Aml = self.env["account.move.line"].browse
        reconciled_bill_ids = self.reconciled_bill_ids + self.reconciled_invoice_ids
        for inv in set(reconciled_bill_ids):
            payments_vals = [p for p in inv._get_reconciled_info_JSON_values()]
            withholding_data = [
                {
                    "account_id": self._get_counterpart_aml(
                        Aml(vals["payment_id"])
                    ).account_id,
                    "amount": Aml(vals["payment_id"]).debit,
                }
                for vals in payments_vals
                if not vals["account_payment_id"]
            ]

            paid_amount = self._get_invoice_reconciled_amount(payments_vals, multi=True)
            total_paid += paid_amount

            dates = [payment["date"] for payment in payments_vals]
            date = max(dates) if dates else False

            withholding_vals["invoices_data"].append(
                {
                    "date_invoice": inv.invoice_date,
                    "payment_id": self.id,
                    "invoice_id": inv.id,
                    "date": date,
                    "payment_amount": round(
                        paid_amount + sum(wh["amount"] for wh in withholding_data), 2
                    ),
                    "reference": inv.l10n_do_fiscal_number,
                    "withholding": withholding_data,
                    "paid_amount": paid_amount,
                }
            )
            wh_values = self._get_withholding_values(wh_values, withholding_data)

        total_paid_amount = total_paid + sum(
            [amount for x, amount in wh_values.items()]
        )
        withholding_vals["amount_in_words"] = self.get_amount_in_words(
            total_paid_amount
        )
        withholding_vals["paid_amount"] = total_paid_amount
        withholding_vals[
            "payments_amount"
        ] = total_paid_amount - self._get_total_withheld(
            withholding_vals["invoices_data"]
        )

        withholding_vals["withholding_values"] = wh_values

        return withholding_vals

    def get_certification_data(self):

        data = getattr(
            self, "_get_%s_withholding_data" % self.l10n_do_withholding_type
        )()

        return data
