# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    internal_services = fields.Boolean()
    internal_services_journal_id = fields.Many2one(
        "account.journal",
        "Invoice Journal",
        help="This journal will be used by default in the invoices of this contact.",
    )
