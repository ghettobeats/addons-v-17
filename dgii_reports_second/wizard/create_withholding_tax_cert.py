# Copyright 2019 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class CreateWithholdingTaxCert(models.TransientModel):
    _name = "create.withholding.tax.cert"
    _description = "Create Withholding Tax Cert Wizard"

    certificate_date = fields.Date(
        string='Fecha de certificado', required=True,
        default=fields.Date.today()
    )

    date_from = fields.Date(
        string='Fecha de inicio', required=True
    )
    date_to = fields.Date(
        string='Fecha final', required=True
    )

    company_id = fields.Many2one(
        'res.company', string='Compañia',
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency', string='Incluir facturas con moneda',
        default=lambda self: self.env.company.currency_id, required=True
    )

    partner_id = fields.Many2one(
        'res.partner', string='Socio de negocio', required=True
    )

    def validate_data(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('"Date from" must be less than or equal to "Date to"'))
        return True


    def get_report_datas(self):
        payments_ids = self.env['account.payment'].search([('state', '=', 'posted'),
                                                     ('withold_method', 'in', ('itbis','isr','itbis_isr')),
                                                       ('currency_id', '=', self.currency_id.id),
                                                       ('date', '>=', self.date_from),
                                                           ('date', '<=', self.date_to),
                                                          ('payment_type','=','outbound'),
                                                           ('company_id','=', self.company_id.id),
                                                           ('partner_id','=',self.partner_id.id)]).ids

        payments_objects = self.env['account.payment'].browse(payments_ids)

        tax_ids = self.env['account.tax'].search([('amount', '<', 0)]).ids

        invoice_ids = self.env['account.move'].search([('state', '=', 'posted'),
                                                     ('invoice_line_ids.tax_ids', 'in', tax_ids),
                                                     ('move_type', '!=', 'entry'),
                                                       ('currency_id', '=', self.currency_id.id),
                                                       ('date', '>=', self.date_from),
                                                           ('date', '<=', self.date_to),
                                                          ('payment_date','!=',False),
                                                           ('company_id','=', self.company_id.id),
                                                           ('partner_id','=',self.partner_id.id)]).ids

        invoice_objects = self.env['account.move'].browse(invoice_ids)

        ret_invoices = []
        withold_isr_amount = 0.0
        withold_itbis_amount = 0.0
        amount = 0.0
        model = self.env.context.get('active_model')
        for pay in payments_objects:
            for invoices in pay.payment_invoice_ids:
                ret_invoices.append({
                    'invoice_id': invoices.invoice_id,
                    'date_invoice': invoices.date_invoice,
                    'subtotal': invoices.subtotal,
                    'itbis': invoices.itbis,
                    'itbis_withold': invoices.itbis_withold,
                    'isr_withold': invoices.isr_withold,
                    'l10n_latam_document_number': invoices.invoice_id.l10n_latam_document_number,
                    'name': pay.name,
                    'payment_date': pay.date,
                    'invoice_name': invoices.invoice_id.name,
                })

            withold_isr_amount += pay.withold_isr_amount
            withold_itbis_amount += pay.withold_itbis_amount
            amount += invoices.subtotal + invoices.itbis - invoices.itbis_withold - invoices.isr_withold

        for inv in invoice_objects:
            ret_invoices.append({
                        'invoice_id': inv.id,
                        'date_invoice': inv.date,
                        'subtotal': inv.amount_untaxed,
                        'itbis': inv.invoiced_itbis,
                        'itbis_withold': inv.withholded_itbis,
                        'isr_withold': inv.income_withholding,
                        'l10n_latam_document_number': inv.l10n_latam_document_number,
                        'name': inv.name,
                        'payment_date': inv.payment_date,
                        'invoice_name': inv.name,
            })

            withold_isr_amount += inv.income_withholding
            withold_itbis_amount += inv.withholded_itbis
            amount += inv.amount_untaxed + inv.invoiced_itbis - inv.income_withholding - inv.withholded_itbis

        return ret_invoices, withold_isr_amount, withold_itbis_amount, amount






    def action_pdf(self):
        ret_invoices, withold_isr_amount, withold_itbis_amount, amount = self.get_report_datas()
        ids = self.read()[0]

        data ={
            'model': 'create.withholding.tax.cert',
            'form': self.read()[0],
            'ret_invoices': ret_invoices,
            'withold_isr_amount': withold_isr_amount,
            'withold_itbis_amount': withold_itbis_amount,
            'amount': amount,
            'partner_id': self.partner_id.name,
            'certificate_date': self.certificate_date,
            # 'company_id': self.company_id,
            'partner_id_vat': self.partner_id.vat,
            'partner_id_street': self.partner_id.street,
            'partner_id_street2': self.partner_id.street2,
            'partner_id_city': self.partner_id.city,
            'partner_id_state_name': self.partner_id.state_id.name,
            'currency_id': self.currency_id.id,
            'report_file_name': 'Certificado de retenciones - ' + self.partner_id.name + ' - Retenciones hasta el ' + \
                                str(self.date_to) + ' - moneda ' + self.currency_id.name ,
            'companyid': self.company_id.id,
            }
        id = data['form']['id']

        wizard = self.env['create.withholding.tax.cert'].browse(id)
        data['docs'] = wizard

        # report = self.env['ir.actions.report']._get_report_from_name('dgii_reports.action_print_tax_cert_daterange')
        # report.report_file = "Prueba"

        return self.env.ref(
            'dgii_reports_second'
            '.action_print_tax_cert_daterange').report_action(
            self, data=data)


    def action_view(self):
        res = {
            'type': 'ir.actions.client',
            'name': 'Certificado de retencion: Rango de fecha',
            'tag': 'tax.cert.wizard',
            'context': {'wizard_id': self.id}
        }
        return res




