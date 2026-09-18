from odoo import models, fields

class CheckReportConfig(models.Model):
    _name = "check.report.config"

    name = fields.Char("Nombre", required=True)
    font_zise = fields.Float(string="Tamaño del las letras", default=15)
    body_top = fields.Float(string="Margen superior del cuerpo del cheque", default=23)
    date_top = fields.Float(string="Margen superior de la fecha", default=4.2)
    date_left = fields.Float(string="Margen izquierdo de la fecha", default=200)
    date_month_left = fields.Float(string="Margen izquierdo el mes de la fecha", default=5)
    date_year_left = fields.Float(string="Margen izquierdo al año de la fecha", default=5)
    name_top = fields.Float(string="Margen superior del nombre", default=21)
    name_left = fields.Float(string="Margen izquierdo del nombre", default=57)
    amount_top = fields.Float(string="Margen superior del monto", default=20)
    amount_left = fields.Float(string="Margen izquierdo del monto", default=192)
    amount_letter_top = fields.Float(string="Margen superior monto en letras", default=31)
    amount_letter_left = fields.Float(string="Margen izquierdo monto en letras", default=20)
    commu_letter_top = fields.Float(string="Margen superior concepto", default=50)
    commu_letter_left = fields.Float(string="Margen izquierdo concepto", default=30)
    check_footer_amount_top = fields.Float("Margen superior de monto en pie", default=50)
    check_footer_amount_left = fields.Float("Margen izquierdo de monto en pie", default=200)