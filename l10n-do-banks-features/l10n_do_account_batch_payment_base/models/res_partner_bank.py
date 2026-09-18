from odoo import models, api
from odoo.osv import expression


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def name_get(self):
        name_array = []
        for record in self:
            name_array.append(
                (
                    record.id,
                    "%s - %s"
                    % (
                        record.partner_id.name if record.partner_id else "",
                        record.acc_number,
                    ),
                )
            )
        return name_array

    @api.model
    def _name_search(
        self, name="", args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        args = args or []
        domain = []
        if name:
            domain = [
                "|",
                ("acc_number", operator, name),
                ("partner_id.name", operator, name),
            ]
        res_ids = self._search(
            expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid
        )
        return res_ids
