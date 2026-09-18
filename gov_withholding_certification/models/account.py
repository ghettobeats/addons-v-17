#  Copyright (c) 2020 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def get_certification_data(self):

        data = super(AccountPayment, self).get_certification_data()

        for invoice in data["invoices_data"]:
            payment_id = self.browse(invoice["payment_id"])
            invoice["release_number"] = payment_id.release_number
            invoice["check_number"] = payment_id.check_number

        return data
