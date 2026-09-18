# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    country_id = fields.Many2one(
        comodel_name='res.country', 
        string='Nacionalidad (país)', 
        groups='hr.group_hr_user', 
        tracking=True,
        default=lambda self: self.env.ref('base.do')  # Reemplaza 'base.do' con el XML ID de República Dominicana
    )

    country_of_birth = fields.Many2one(
        comodel_name='res.country', 
        string='País de nacimiento', 
        groups='hr.group_hr_user',
        tracking=True,
        default=lambda self: self.env.ref('base.do')  # Reemplaza 'base.do' con el XML ID de República Dominicana
    )

    private_country_id = fields.Many2one(
        comodel_name='res.country', 
        string='País', 
        groups='hr.group_hr_user',
        default = lambda self: self.env.ref('base.do')  # Reemplaza 'base.do' con el XML ID de República Dominicana
    )

    identification_id = fields.Char(
        string='Identification No',  # Etiqueta del campo en la interfaz
        groups="hr.group_hr_user",  # Define qué grupos de usuarios tienen acceso a este campo
        tracking=True,  # Habilita el seguimiento de cambios en el campo
        help="Enter the employee ID in the format 000-0000000-0",  # Explicación para el usuario
        required=True,  # Campo obligatorio
        size=13,  # Tamaño máximo del campo
    )

    zone_id = fields.Many2one(
        comodel_name='hr.zone',
        string='Zone',
        help="Select the zone or location where the employee will work. This may include areas such as offices, plants, or specific regions."
    )

    region_id = fields.Many2one(
        comodel_name='hr.region',
        string='Region',
        help="Select the geographic region where the employee is assigned, for example, a province, state, or country."
    )

    structure_class_id = fields.Many2one(
        comodel_name='hr.structure.class',
        required=True, tracking=True,
        string='Class',
        help="Select the employee class according to the organizational structure, such as administrative, operational, managerial, among others."
    )

    def _format_identification(self, value):
        """Formatea el valor de identificación en el formato 000-0000000-0."""
        value = re.sub(r'\D', '', value)  # Elimina todos los caracteres no numéricos
        value = value.zfill(11)  # Asegura que el ID tenga 11 dígitos
        return f"{value[:3]}-{value[3:10]}-{value[10]}" if len(value) == 11 else value

    @api.model
    def create(self, vals):
        if 'identification_id' in vals and vals['identification_id']:
            # Elimina cualquier carácter no numérico
            vals['identification_id'] = re.sub(r'\D', '', vals['identification_id'])
            # Asegura que tenga 11 dígitos agregando ceros iniciales si es necesario
            vals['identification_id'] = vals['identification_id'].zfill(11)
            if len(vals['identification_id']) != 11:
                raise ValidationError(_("El número de identificación debe tener exactamente 11 caracteres."))
            vals['identification_id'] = self._format_identification(vals['identification_id'])
        return super(HrEmployee, self).create(vals)

    def write(self, vals):
        if 'identification_id' in vals and vals['identification_id']:
            # Elimina cualquier carácter no numérico
            vals['identification_id'] = re.sub(r'\D', '', vals['identification_id'])
            # Asegura que tenga 11 dígitos agregando ceros iniciales si es necesario
            vals['identification_id'] = vals['identification_id'].zfill(11)
            if len(vals['identification_id']) != 11:
                raise ValidationError(_("El número de identificación debe tener exactamente 11 caracteres."))
            vals['identification_id'] = self._format_identification(vals['identification_id'])
        return super(HrEmployee, self).write(vals)

    @api.constrains('identification_id')
    def _check_identification_format(self):
        pattern = re.compile(r'^\d{3}-\d{7}-\d{1}$')
        for record in self:
            if record.identification_id and not pattern.match(record.identification_id):
                raise ValidationError("El número de identificación debe tener el formato 000-0000000-0")

    
    _order = 'identification_id'
    _sql_constraints = [('identification_id_uniq', 'unique (identification_id)', 'The vat must be unique')]

class HrZone(models.Model):
    _name = 'hr.zone'
    _description = 'name of the areas'

    name = fields.Char(
        string='Description',
        size=128,
        help='that is, name of the areas.',
        required=True
    )

    region_id = fields.Many2one(
        comodel_name='hr.region',
        string='Region',
        required=True,
        help="Select the geographic region where the employee is assigned, for example, a province, state, or country."
    )

    code = fields.Char(
        string='Código',
        size=128,
        help='that is, code according to your area.'
    )

    _order = 'name'
    _sql_constraints = [('name_uniq', 'unique (name)', 'The zone name must be unique')]

class StructureClass(models.Model):
    _name = 'hr.structure.class'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'class structure'

    name = fields.Char(
        string='Structure Description Class',
        size=128,
        help='i.e. the name of the class structure.',
        required=True
    )

    code = fields.Char(
        string='Código',
        size=128,
        help='that is, code according of the class structure.'
    )

    _order = 'name'
    # _sql_constraints = [('name_uniq', 'unique (name)', 'The name to structure class must be unique')]

class HRReion(models.Model):
    _name = 'hr.region'
    _description = 'name of the region'

    name = fields.Char(
        string='Description Region',
        size=128,
        help='i.e. the name of the region.',
        required=True
    )

    code = fields.Char(
        string='Código',
        size=128,
        help='that is, code according of the region.'
    )

    _order = 'name'
    _sql_constraints = [('name_uniq', 'unique (name)', 'The name to structure class must be unique')]

