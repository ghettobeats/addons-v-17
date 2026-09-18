# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _get_default_journal(self):
        res = super()._get_default_journal()
        if (
            self.env.context.get("default_type") == "out_invoice"
            and self.env.context.get("active_model") == "sale.order"
            and self.env.context.get("active_id")
        ):
            sale_order = self.env["sale.order"].browse(self.env.context["active_id"])
            customer = sale_order.partner_id
            if customer.internal_services:
                return customer.internal_services_journal_id
        return res

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        res = super()._onchange_partner_id()
        if (
            self.type in ["out_invoice", "out_refund"]
            and self.partner_id
            and self.partner_id.internal_services
        ):
            self.journal_id = self.partner_id.internal_services_journal_id
        if isinstance(res, dict) and res.get("warning"):
            return res

    def post(self):
        out_invoices = all(
            [move_type == "out_invoice" for move_type in self.mapped("type")]
        )
        if self and out_invoices:
            for invoice in self:
                res = super(
                    AccountMove,
                    invoice.with_context(
                        partner_internal_services=invoice.partner_id.internal_services,
                        move_type=invoice.type,
                    ),
                ).post()
        else:
            res = super().post()
        return res
