
from odoo import models, fields


class Purchase_Order_inherit(models.Model):
     _inherit = 'purchase.order'

     certification_number = fields.Char("Certification Number")
     contract_number = fields.Char("Contract Number")
     contract_date_from = fields.Date("Effective Date")
     contract_date_end  = fields.Date("Expiration Date")
     is_contract = fields.Boolean("is contract?")
