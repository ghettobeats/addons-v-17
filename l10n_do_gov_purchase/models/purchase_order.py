from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    portal_order_number = fields.Char()
    record_number = fields.Char()
    contract_number = fields.Char()
    purchase_mode = fields.Selection(
        [  # DEPRECATED: do not forward port to v13.
            ("Purchases below threshold", "Purchases Below Threshold"),
            ("international competitive bidding", "International Competitive Bidding"),
            ("reverse auction", "Reverse Auction"),
            ("exception processes", "Exception Processes"),
            (
                "national security exception processes",
                "National Security Exception Processes",
            ),
            ("public tender", "Public Tender"),
            ("restricted tender", "Restricted Tender"),
            ("draw of works", "Draw of Works"),
            ("price comparison", "Price comparison"),
            ("minor purchase", "Minor purchase"),
            ("international public bidding", "International Public Bidding"),
        ]
    )
    purchase_mode_id = fields.Many2one("purchase.gov.purchase.mode", "Purchase Mode")

    def init(self):
        """
            matches the value of purchase_mode selection field
            with its record in purchase.gov.purchase.mode.
            Repla
        """
        order_ids = self.sudo().search([("purchase_mode", "!=", False)])
        for order_id in order_ids:
            if order_id.purchase_mode:
                mode_id = self.env.ref(
                    "l10n_do_gov_purchase.purchase_mode_"
                    + order_id.purchase_mode.replace(" ", "_"),
                    False,
                )
                if mode_id:
                    order_id.write(
                        {"purchase_mode_id": mode_id.id, "purchase_mode": False}
                    )
            else:
                continue


class PurchaseMode(models.Model):
    _name = "purchase.gov.purchase.mode"
    _description = "Purchase Mode"

    name = fields.Char("Name", translate=True)
