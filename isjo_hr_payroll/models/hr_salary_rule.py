# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _description = 'Reglas Salariales Personalizadas'  # Si deseas modificar la descripción

    column_display_total_on_report = fields.Selection([
        ('total', 'Total'),
        ('amount', 'Importe'),
        ('quantity', 'Cantidad')],
        string='Column showing the total in the report', default='total', required=True,
        help="Indica la columna donde se va a mostrar el valor del total en el reporte de comprobantes de pago.")

    is_clone = fields.Boolean(
        'Is a clone', default=False,
        help='Indica que esta regla es clon de otra regla existente.')

    cloned_salary_rule_id = fields.Many2one(
        'hr.salary.rule', string='Cloned rule', help='Regla la cual se clonará.',
        domain="[('id', '!=', id), ('is_clone','=',False)]", ondelete='cascade')

    clones_ids = fields.One2many(
        'hr.salary.rule', 'cloned_salary_rule_id', string='Clones')

    # NUEVO CAMPO: Mapeo a columnas del reporte TSS
    tss_report_column = fields.Selection([
        ('salario_cot', 'Salario Cotizable (TSS)'),
        ('salario_isr', 'Salario ISR (DGII)'),
        ('otras_rem', 'Otras Remuneraciones'),
        ('salario_infotep', 'Salario INFOTEP'),
        ('aporte_vol', 'Aporte Voluntario'),
        ('saldo_period', 'Saldo a favor del periodo'),
        ('regalia_pascual', 'Regalía Pascual'),
        ('preaviso_cesantia', 'Preaviso/Cesantía/Indemnización'),
        ('retencion_pension', 'Retención Pensión Alimenticia'),
        ('no_aplica', 'No Aplica (No incluir en TSS)')
    ], string='Columna Reporte TSS', default='no_aplica', required=True,
        help="Especifica a qué columna del reporte de Autodeterminación TSS corresponde esta regla salarial.")

    # Campo para indicar si es una regla que debe sumarse (por defecto True)
    tss_sum_in_column = fields.Boolean(
        string='Sumar en columna TSS',
        default=True,
        help="Si está marcado, el valor de esta regla se sumará al total de la columna seleccionada.")

    # Campo para ordenamiento en el reporte (opcional)
    tss_sequence = fields.Integer(
        string='Secuencia TSS',
        default=10,
        help="Orden de prioridad para esta regla en el reporte TSS (menor número = mayor prioridad)")

    @api.onchange('cloned_salary_rule_id')
    def _onchange_cloned_salary_rule_id(self):
        if self.cloned_salary_rule_id:
            salary_rule_id = self.cloned_salary_rule_id
            self.name = salary_rule_id.name
            self.category_id = salary_rule_id.category_id
            self.code = salary_rule_id.code
            self.sequence = salary_rule_id.sequence
            self.appears_on_payslip = salary_rule_id.appears_on_payslip
            self.condition_select = salary_rule_id.condition_select
            self.condition_range = salary_rule_id.condition_range
            self.condition_range_min = salary_rule_id.condition_range_min
            self.condition_range_max = salary_rule_id.condition_range_max
            self.condition_python = salary_rule_id.condition_python
            self.amount_select = salary_rule_id.amount_select
            self.amount_percentage_base = salary_rule_id.amount_percentage_base
            self.quantity = salary_rule_id.quantity
            self.amount_fix = salary_rule_id.amount_fix
            self.amount_percentage = salary_rule_id.amount_percentage
            self.amount_python_compute = salary_rule_id.amount_python_compute
            self.partner_id = salary_rule_id.partner_id
            self.note = salary_rule_id.note
            self.account_debit = salary_rule_id.account_debit
            self.account_credit = salary_rule_id.account_credit
            self.analytic_account_id = salary_rule_id.analytic_account_id
            self.not_computed_in_net = salary_rule_id.not_computed_in_net
            # NUEVO: Heredar también la configuración TSS
            self.tss_report_column = salary_rule_id.tss_report_column
            self.tss_sum_in_column = salary_rule_id.tss_sum_in_column
            self.tss_sequence = salary_rule_id.tss_sequence

    def write(self, vals):
        for record in self:
            # Llamamos al método write de la clase base para cada registro individualmente
            res = super(HrSalaryRule, record).write(vals)

            # Si se modificó la columna TSS, verificar consistencia con clones
            if 'tss_report_column' in vals and not record.is_clone and record.clones_ids:
                # Verificar que todos los clones tengan la misma columna
                for clone in record.clones_ids:
                    if clone.tss_report_column != vals.get('tss_report_column', record.tss_report_column):
                        # Actualizar el clon automáticamente
                        clone.write({'tss_report_column': vals.get('tss_report_column', record.tss_report_column)})

            # Aseguramos que el registro no sea un clon y que tenga clones para actualizar
            if hasattr(record, 'is_clone') and not record.is_clone and record.clones_ids:
                # Recorremos los clones y aplicamos los cambios a cada uno
                for rec in record.clones_ids:
                    rec.write(vals)

        return res

    def show_clone_salary_rule_wizard(self):
        active_ids = self._context.get('active_ids', False)
        return dict(
            type='ir.actions.act_window',
            name=_('Clonar Reglas Salariales'),
            res_model='clone.salary.rule.wizard',
            target='new',
            view_mode='form',
            context={'active_ids': active_ids}
        )

    # Restricción: Solo las reglas clonadas pueden tener el mismo mapeo que su regla padre
    @api.constrains('tss_report_column', 'is_clone', 'cloned_salary_rule_id')
    def _check_tss_column_clone(self):
        for record in self:
            # Solo validar si es un clon Y tiene regla original Y los campos están en contexto de escritura
            if record.is_clone and record.cloned_salary_rule_id and record.tss_report_column:
                # Si el campo fue modificado manualmente en el clon, verificar que coincida
                if record.tss_report_column != record.cloned_salary_rule_id.tss_report_column:
                    # Permitir que sea diferente SOLO si es un valor válido y se está creando
                    if record.create_date and record.tss_report_column != 'no_aplica':
                        raise ValidationError(_(
                            "Las reglas clonadas deben mantener la misma asignación de columna TSS "
                            "que la regla original. La regla original '%s' tiene asignada '%s'.\n\n"
                            "Si necesita una configuración diferente, debe crear una regla nueva no clonada."
                        ) % (record.cloned_salary_rule_id.name,
                             record.cloned_salary_rule_id.get_tss_column_display()))

    # Restricción: No permitir múltiples reglas no clonadas con la misma columna (opcional)
    @api.constrains('tss_report_column', 'is_clone')
    def _check_unique_tss_column(self):
        """Restricción: No permitir múltiples reglas no clonadas con la misma columna"""
        for record in self:
            # Solo verificamos para reglas que NO son clones y que no son 'no_aplica'
            if not record.is_clone and record.tss_report_column and record.tss_report_column != 'no_aplica' and record.tss_report_column != 'otras_rem' and record.tss_report_column != 'salario_cot':
                # Buscar otras reglas no clonadas con la misma columna
                duplicate_rules = self.search([
                    ('id', '!=', record.id),
                    ('is_clone', '=', False),
                    ('tss_report_column', '=', record.tss_report_column),
                    ('tss_report_column', '!=', 'no_aplica')
                ])

                if duplicate_rules:
                    rule_names = ', '.join(duplicate_rules.mapped('name'))

                    # Obtener el nombre mostrado de la columna TSS
                    column_display = ''
                    if record.tss_report_column:
                        selection_dict = dict(record._fields['tss_report_column'].selection)
                        column_display = record._get_tss_column_display() if hasattr(record, '_get_tss_column_display') else record.tss_report_column
                        # column_display = selection_dict.get(record.tss_report_column, record.tss_report_column)

                    raise ValidationError(_(
                        "Ya existe otra regla no clonada con la misma columna TSS '%s'.\n"
                        "Reglas existentes: %s\n\n"
                        "Las reglas no clonadas deben tener asignaciones únicas. "
                        "Si necesita múltiples reglas para la misma columna, debe clonarlas."
                    ) % (column_display, rule_names))

    def _get_tss_column_display(self):
        """Helper para obtener el valor mostrado de la columna TSS"""
        self.ensure_one()
        if self.tss_report_column:
            selection_dict = dict(self._fields['tss_report_column'].selection)
            return selection_dict.get(self.tss_report_column, self.tss_report_column)
        return ''
