# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import models, fields, api, _
from datetime import datetime

_logger = logging.getLogger(__name__)

# Diccionario para traducir los meses del inglés al español
MES_EN_ESPANOL = {
    "January": "Enero", "February": "Febrero", "March": "Marzo",
    "April": "Abril", "May": "Mayo", "June": "Junio",
    "July": "Julio", "August": "Agosto", "September": "Septiembre",
    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
}


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def assign_rule_in_lote(self):
        """Asigna y refresca las novedades de acuerdo con lote seleccionado y recibos."""
        # Solo procesar novedades en estado 'confirm'
        for batch in self:
            if batch.state not in ('verify', 'draft'):
                continue
            for record in batch.slip_ids:
                record._remove_invalid_inputs(payslip=record)
                record._add_fixed_inputs(payslip=record)
                record.compute_sheet()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals:
                structure = self.env['hr.payroll.structure'].sudo().browse(vals.get('struct_id'))
                date_obj = fields.Date.from_string(vals.get('date_start'))

                # Formatea la fecha en inglés
                month_year = date_obj.strftime('%B-%Y')

                # Traduce el mes usando el diccionario
                month, year = month_year.split('-')
                period = f"{MES_EN_ESPANOL.get(month, month)}-{year}"

                vals['name'] = f"{structure.name} - {period}"
        # for vals in vals_list:
        #     if 'name' not in vals:
        #         structure = self.env['hr.payroll.structure'].sudo().browse(vals.get('struct_id'))
        #         period = fields.Date.from_string(vals.get('date_start')).strftime('%B-%Y')
        #         vals['name'] = f"{structure.name} - {period}"

        return super(HrPayslipRun, self).create(vals_list)

    @api.onchange('struct_id', 'date_start')
    def _onchange_structure_or_date(self):
        if self.struct_id and self.date_start:
            structure = self.struct_id
            date_obj = fields.Date.from_string(self.date_start)

            # Formatear la fecha en inglés
            month_year = date_obj.strftime('%B-%Y')

            # Traducir el mes usando el diccionario
            month, year = month_year.split('-')
            period = f"{MES_EN_ESPANOL.get(month, month)}-{year}"

            self.name = f"{structure.name} - {period}"  # Reemplaza <nombre_del_campo> por el campo donde quieres guardar la fecha en español
        # if self.struct_id and self.date_start:
        #     period = fields.Date.from_string(self.date_start).strftime('%B-%Y')
        #     self.name = f"{self.struct_id.name} - {period}"

    _sql_constraints = [
        ('name_uniq',
         'UNIQUE(name)',
         'Los nombres deben ser únicos para los Lotes!'),
    ]

    _order = 'date_end desc, name asc'

    # def action_draft(self):
    #     slips = self.slip_ids.filtered(lambda slip: slip.state != 'done')
    #
    #     for slip in slips:
    #         slip.action_payslip_cancel()
    #         slip.action_payslip_draft()
    #
    #     return super(HrPayslipRun, self).action_draft()
    #
    # def re_calculate(self):
    #     for slip in self.slip_ids:
    #         if slip.state != 'done':
    #             slip.refresh_inputs()
    #             slip.compute_sheet()
    #
    #     msg = 'Recalculado'
    #     self.message_post(body=msg)
    #
    # def verify_payslips(self):
    #     for slip in self.slip_ids:
    #         if slip.state not in ('done', 'cancel'):
    #             slip.action_payslip_verify()
    #
    #     msg = 'Marcado como Revisado'
    #     self.message_post(body=msg)
    #     return self.write({'state': 'verify'})
    #
    # def remove_slips(self):
    #     num = len(self.slip_ids)
    #     slips = self.slip_ids.filtered(lambda slip: slip.state not in ('done', 'verify'))
    #     slips.unlink()
    #     msg = '%s Nominas Borradas' % num
    #     self.message_post(body=msg)
    #
    # def cancel_and_draft(self):
    #     for slip in self.slip_ids:
    #         slip.move_id.button_cancel()
    #         slip.state = 'verify'
    #         slip.action_payslip_cancel()
    #         slip.action_payslip_draft()
    #
    #     self.action_draft()
    #
    # def send_payslip_by_email(self):
    #     self.slip_ids.send_payslip_by_email()
