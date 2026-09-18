# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetMovementHistory(models.Model):
    _name = "fleet.movement.history"
    _description = "Historial de Aprobaciones de Movimiento Vehicular"
    _order = "date desc"
    _rec_name = "vehicle_id"

    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehiculo", ondelete="cascade", index=True)
    movement_state = fields.Selection([
        ("draft",      "Borrador"),
        ("assigned",   "Asignado"),
        ("discharged", "Descargado"),
        ("cancelled",  "Cancelado"),
    ], string="Estado del Movimiento")
    action = fields.Selection([
        ("requested",  "Solicitud Enviada"),
        ("approved",   "Aprobado"),
        ("rejected",   "Rechazado"),
        ("cancelled",  "Cancelado"),
        ("restarted",  "Reiniciado"),
    ], string="Accion")
    done_by = fields.Many2one("res.users", string="Realizado por")
    assignee_id = fields.Many2one("hr.employee", string="Asignado A")
    driver_id = fields.Many2one("hr.employee", string="Conductor")
    comment = fields.Char(string="Comentario")
    date = fields.Datetime(string="Fecha", default=fields.Datetime.now)
