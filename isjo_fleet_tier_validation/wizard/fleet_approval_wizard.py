# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class FleetApprovalWizard(models.TransientModel):
    _name = "fleet.approval.wizard"
    _description = "Wizard de Aprobacion de Movimiento Vehicular"

    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehiculo", readonly=True)
    action = fields.Selection([
        ("approve", "Aprobar"),
        ("reject",  "Rechazar"),
    ], string="Accion", readonly=True)
    comment = fields.Char(string="Comentario", required=True)
    movement_state = fields.Selection(related="vehicle_id.movement_state", readonly=True)
    pending_assignee_id = fields.Many2one(related="vehicle_id.pending_assignee_id", readonly=True)
    assigned_person_id = fields.Many2one(related="vehicle_id.assigned_person_id", readonly=True)

    def action_confirm(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        sequences = vehicle._get_sequences_to_approve(self.env.user)
        reviews = vehicle.review_ids.filtered(
            lambda r: r.sequence in sequences or r.approve_sequence_bypass
        )
        if not reviews:
            raise UserError(_("No hay revisiones pendientes para este usuario."))

        reviews.write({"comment": self.comment})

        if self.action == "approve":
            vehicle._validate_tier(reviews)
            vehicle._update_counter({"review_deleted": True})
            vehicle._fleet_post_approval_history(self.comment)
            if vehicle.validated:
                vehicle._fleet_apply_approved_state()
        else:
            vehicle._rejected_tier(reviews)
            vehicle._update_counter({"review_deleted": True})
            vehicle._fleet_log_movement("rejected", self.comment)
