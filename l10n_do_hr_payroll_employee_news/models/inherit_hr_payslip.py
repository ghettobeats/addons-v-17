# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    def assign_rule_in_lote(self):
        """Asigna y refresca las novedades de acuerdo con el recibo seleccionado y el empleado."""
        for record in self:
            # Solo procesar novedades en estado 'confirm'
            if record.state not in ('verify', 'draft'):
                continue
            record._remove_invalid_inputs(payslip=record)
            record._add_fixed_inputs(payslip=record)
            record.compute_sheet()

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super(HrPayslipInherit, self).create(vals_list)
        for payslip in payslips:
            self._add_fixed_inputs(payslip)
            payslip.compute_sheet()
        return payslips

    def write(self, vals):
        res = super(HrPayslipInherit, self).write(vals)
        if 'struct_id' in vals:
            for payslip in self:
                self._remove_invalid_inputs(payslip)
                self._add_fixed_inputs(payslip)
                self.compute_sheet()
        return res

    def _add_fixed_inputs(self, payslip):
        """
        Buscar todas las novedades aplicables al empleado basándose en:
        - Fechas (start_date y end_date).
        - Pertenencia a un lote si no tienen fechas.
        - Lote asociado al payslip, si aplica.
        """
    
        # Construir el dominio básico para buscar novedades
        domain = [
            ('employee_id', '=', payslip.employee_id.id),  # Novedades del empleado específico
            ('state', '=', 'assign'),  # Novedades asignadas
            '|',  # Manejo de condiciones opcionales para start_date y end_date
            '&',  # Ambas condiciones deben cumplirse
            ('start_date', '<=', payslip.date_to),  # La fecha de inicio no es después del fin del periodo
            ('start_date', '>=', payslip.date_from),  # La fecha de inicio no es antes del inicio del periodo
            '|',
            ('end_date', '=', False),  # Novedades sin fecha de fin
            ('end_date', '>=', payslip.date_from),  # Fecha de fin incluye el inicio del periodo
        ]
    
        # Si el payslip tiene un lote asociado, buscar novedades que también pertenezcan al lote
        # if payslip.payslip_run_id and not payslip.date_from or payslip.date_to:
        #     domain = ['|'] + domain + [('apply_in', '=', payslip.payslip_run_id.id)]
    
        # Buscar novedades válidas basadas en el dominio
        novedades_validas = self.env['payslip.input.import'].search(domain)

        # Filtrar por estructura de nómina directamente en Python para evitar sobrecarga de consulta
        novedades_validas = novedades_validas.filtered(
            lambda e: payslip.struct_id.id in e.input_id.struct_ids.ids
        )

        # Añadir las entradas encontradas al payslip y actualizar las notas
        for entrada in novedades_validas:
            self.env['hr.payslip.input'].create({
                'name': entrada.input_id.name or 'Novedad',  # Nombre o descripción
                'payslip_id': payslip.id,  # Nómina asignada
                'input_type_id': entrada.input_id.id,  # Tipo de entrada
                'amount': entrada.amount,  # Importe de la novedad
                'sequence': 10,  # Secuencia por defecto
            })
            # Actualizar las notas de la novedad
            entrada.notes = "{}\nSe ha asignado al Batch/Lote/Recibo: {}".format(
                entrada.notes or '', payslip.name
            )

    def _remove_invalid_inputs(self, payslip):
        # Eliminar entradas que no pertenecen a la nueva estructura
        payslip.input_line_ids.unlink()
