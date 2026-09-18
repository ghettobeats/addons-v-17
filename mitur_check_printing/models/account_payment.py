from odoo import models, fields, api, _
from odoo.tools.misc import  formatLang, format_date

class account_payment(models.Model):
    _inherit = "account.payment"
    
    check_name = fields.Char(string="Name on Check", help="Name on printed check")

    def _check_build_page_info(self, i, p):
        multi_stub = self.company_id.account_check_printing_multi_stub
        check_layout = self.company_id.account_check_printing_layout
        if check_layout == 'mitur_check_printing.action_print_custom_report':
            return {
                'sequence_number': self.check_number,
                'manual_sequencing': self.journal_id.check_manual_sequencing,
                'date': format_date(self.env, self.date),
                'partner_id': self.partner_id,
                'partner_name': self.check_name,
                'currency': self.currency_id,
                'state': self.state,
                'amount': formatLang(self.env, self.amount, currency_obj=self.currency_id) if i == 0 else 'VOID',
                'amount_in_word': self.check_amount_in_words if i == 0 else 'VOID',
                'memo': self.ref,
                'stub_cropped': not multi_stub and len(self.move_id._get_reconciled_invoices()) > 9,
                # If the payment does not reference an invoice, there is no stub line to display
                'stub_lines': p,
            }
        return super(account_payment, self)._check_build_page_info(i, p)

class AccountJournal(models.Model):
    _inherit = "account.journal"
    _name = "account.journal"

    check_layout = fields.Many2one(
        "check.report.config", string="Plantilla de cheque", required=False,
        help="Seleccione el formato que corresponde al papel "
        "de verificación va a imprimir sus cheques en.\n"
        "Para desactivar la función de impresión, seleccione 'Ninguno'.")
