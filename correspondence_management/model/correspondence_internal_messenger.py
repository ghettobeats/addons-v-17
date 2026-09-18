from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError

class InternalMessenger(models.Model):
    _name = 'correspondence.internal.messenger'
    _description = 'InternalDelivery'


    employee_id =  fields.Many2one(
        comodel_name='hr.employee',
        string='Empleado',
        required=False)
    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='Puesto de trabajo',
        required=False)
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='Departamento',
        required=False)

    @api.constrains("employee_id")
    def _compute_full_name(self):
        for rec in self:
            if rec.employee_id:
                rec.job_id = rec.employee_id.job_id.id
                rec.department_id = rec.employee_id.department_id.id


    @api.model
    def create(self, values):
        rec = self.env["correspondence.internal.messenger"].search([])
        if len(rec) != 0:
            raise UserError("No puede crear mas de un registro, favor modificar el ya existente.")
        else:
         return super(InternalMessenger, self).create(values)