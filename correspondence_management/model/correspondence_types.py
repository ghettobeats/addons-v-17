from odoo import models, fields, api
import  random

class CorrespondenceTypes(models.Model):
    _name = 'correspondence.types'

    name = fields.Char("Tipo")
    description = fields.Char("Descripción")
    color = fields.Integer(string='Color', readonly=True)

    @api.model
    def create(self, values):
        values['color'] = random.randint(1,9)
        return super(CorrespondenceTypes, self).create(values)