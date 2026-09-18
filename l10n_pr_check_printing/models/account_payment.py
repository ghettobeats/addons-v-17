from odoo import models, api, _
from odoo.tools.misc import format_date


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _check_make_stub_line(self, invoice):
        """ Return the dict used to display an invoice/refund in the stub
        """
        page = super(AccountPayment, self)._check_make_stub_line(invoice)
        page.update(
            {
                "date_invoice": format_date(self.env, invoice.date_invoice),
                "reference_invoice": invoice.reference or "-",
                "number": invoice.number,
            }
        )
        return page

    def _check_build_page_info(self, i, p):
        page = super(AccountPayment, self)._check_build_page_info(i, p)
        page.update(
            {
                "partner_street": self.partner_id.street,
                "partner_street2": self.partner_id.street2,
                "partner_city": self.partner_id.city,
                "partner_state": self.partner_id.state_id.code,
                "partner_zip": self.partner_id.zip,
            }
        )
        return page

    @api.multi
    def do_print_checks(self):
        if self:
            check_layout = self[0].company_id.account_check_printing_layout
            # A config parameter is used to give the ability to use this check format
            # even in other countries than US, as not all the localizations have one
            if check_layout != "disabled" and (
                self[0].journal_id.company_id.country_id.code == "PR"
            ):
                self.write({"state": "sent"})
                return self.env.ref(
                    "l10n_pr_check_printing.%s" % check_layout
                ).report_action(self)
        return super(AccountPayment, self).do_print_checks()
