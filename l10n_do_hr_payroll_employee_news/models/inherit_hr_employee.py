# -*- coding: utf-8 -*-

import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def assign_contact(self):
        for record in self:
            partner = record.env["res.partner"].search([("name", "=", record.name)])
            if partner:
                record.update({"address_home_id": partner.id})
                print('receivable ' + str(self.company_id.hr_payroll_account_charge.name))
                print('payable ' + str(self.company_id.hr_payroll_account_pay.id))
                partner.write({
                    "property_account_receivable_id": self.company_id.hr_payroll_account_charge.id,
                    "property_account_payable_id": self.company_id.hr_payroll_account_pay.id
                })
                bank_account = record.env["res.partner.bank"].search(
                    [
                        ("partner_id", "=", partner.id),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", self.env.company.id),
                    ]
                )
                if bank_account:
                    record.update({"bank_account_id": bank_account.id})
