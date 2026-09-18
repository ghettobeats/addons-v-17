# Copyright 2021-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    cash_replenishment = fields.Boolean(
        "Cash Replenishment", readonly=True, states={"draft": [("readonly", False)]}
    )
    refunded = fields.Boolean()
    cash_replenishment_payment_ids = fields.Many2many(
        "account.payment",
        "cash_replenishment_payments_rel",
        "payment_id",
        "replenishment_payment_id",
        "Payments",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    cash_replenishment_payment_invoice_ids = fields.Many2many(
        "account.move",
        string="Payment Invoices",
        compute="_compute_cash_replenishment_payment_invoice_ids",
    )
    journal_cash_control = fields.Boolean(related="journal_id.cash_control")
    user_can_edit_amount = fields.Boolean(
        compute="_compute_user_can_edit_amount",
        help="Technical field to know if the environment user belongs to group Edit refund amount",
    )

    @api.depends("cash_replenishment_payment_ids")
    def _compute_cash_replenishment_payment_invoice_ids(self):
        for record in self:
            record.cash_replenishment_payment_invoice_ids = False
            if record.cash_replenishment_payment_ids:
                record.cash_replenishment_payment_invoice_ids = (
                    record.cash_replenishment_payment_ids.payment_id.mapped(
                        "reconciled_invoice_ids"
                    )
                    + record.cash_replenishment_payment_ids.payment_id.mapped(
                        "reconciled_bill_ids"
                    )
                )

    @api.depends("payment_type", "state", "cash_replenishment_payment_ids")
    def _compute_user_can_edit_amount(self):
        """Compute boolean field user_can_edit_amount."""
        for record in self:
            record.user_can_edit_amount = self.env.user.has_group(
                "account_payment_cash_custom_workflow.group_account_payment_edit_refund_amount"
            )

    @api.onchange("cash_replenishment")
    def _onchange_cash_replenishment(self):
        """Change domain of fields `destination_journal_id` and `cash_replenishment_payment_ids`
        when the field cash_replenishment is True."""
        attrs_field_destination_journal_id = (
            self.fields_get(["destination_journal_id"])
            and self.fields_get(["destination_journal_id"])["destination_journal_id"]
        )
        destination_journal_domain = attrs_field_destination_journal_id.get("domain")
        if self.cash_replenishment:
            if destination_journal_domain:
                domain_str_part1 = destination_journal_domain[:-1]
                domain_str_part2 = ", ('cash_control', '=', True)"
                destination_journal_new_domain = "%s%s]" % (
                    domain_str_part1,
                    domain_str_part2,
                )
            else:
                destination_journal_new_domain = "[('cash_control', '=', True)]"
            return {
                "domain": {
                    "destination_journal_id": destination_journal_new_domain,
                    "cash_replenishment_payment_ids": [
                        ("refunded", "=", False),
                        ("journal_id.cash_control", "=", True),
                    ],
                }
            }
        else:
            return {
                "domain": {
                    "destination_journal_id": destination_journal_domain,
                    "cash_replenishment_payment_ids": "[]",
                }
            }

    @api.onchange("cash_replenishment_payment_ids")
    def _onchange_cash_replenishment_payment_ids(self):
        """Change field amount with sum total of payments selected."""
        self.amount = False
        if self.cash_replenishment_payment_ids:
            amount_total = sum(self.cash_replenishment_payment_ids.mapped("amount"))
            self.amount = amount_total

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for rec in self:
            if (
                rec.state != "draft"
                and rec.is_internal_transfer
                and rec.cash_replenishment
            ):
                rec.cash_replenishment_payment_ids.write({"refunded": True})
        return res

    def action_draft(self):
        res = super().action_draft()
        for rec in self:
            if (
                rec.state == "draft"
                and rec.is_internal_transfer
                and rec.cash_replenishment
            ):
                rec.cash_replenishment_payment_ids.write({"refunded": False})
        return res

    def cancel(self):
        res = super().cancel()
        for rec in self:
            if rec.state == "draft" and rec.is_internal_transfer:
                rec.cash_replenishment_payment_ids.filtered(
                    lambda payment: payment.refunded
                ).write({"refunded": False})
        return res
