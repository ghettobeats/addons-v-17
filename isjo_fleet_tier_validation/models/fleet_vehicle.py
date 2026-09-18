# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Campos siempre editables sin importar el estado del flujo de validacion
ALWAYS_EDITABLE = ["state_id", "mitur_status", "pending_assignee_id", "assigned_person_id"]


class FleetVehicle(models.Model):
    _inherit = ["fleet.vehicle", "tier.validation"]
    _name = "fleet.vehicle"

    def _auto_init(self):
        result = super()._auto_init()
        self.env.cr.execute(
            "UPDATE fleet_vehicle SET movement_state = 'draft' WHERE movement_state IS NULL"
        )
        return result

    # -------------------------------------------------------------------------
    # Estado del flujo
    # -------------------------------------------------------------------------
    movement_state = fields.Selection(
        selection=[
            ("draft",      "Borrador"),
            ("assigned",   "Asignado"),
            ("discharged", "Descargado"),
            ("cancelled",  "Cancelado"),
        ],
        string="Estado de Movimiento",
        default="draft",
        tracking=True,
        copy=False,
    )

    pending_assignee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Asignar A (Institucional)",
        copy=False,
        tracking=True,
        # domain=[
        #     "|", "|", "|",
        #     ("job_title", "ilike", "encargado"),
        #     ("job_title", "ilike", "director"),
        #     ("job_title", "ilike", "viceministro"),
        #     ("job_title", "ilike", "ministro"),
        # ],
        help="Responsable institucional al que se asignara el vehiculo al aprobarse.",
    )
    pending_assignee_position = fields.Char(
        related="pending_assignee_id.job_title",
        string="Cargo (Solicitado)",
        store=False,
    )

    fleet_responsible_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Responsable Institucional",
        readonly=True,
        copy=False,
        tracking=True,
    )
    fleet_responsible_position = fields.Char(
        related="fleet_responsible_id.job_title",
        string="Cargo (Responsable)",
        readonly=True,
        store=False,
    )

    # -------------------------------------------------------------------------
    # Historial de movimientos
    # -------------------------------------------------------------------------
    movement_history_ids = fields.One2many(
        comodel_name="fleet.movement.history",
        inverse_name="vehicle_id",
        string="Historial de Aprobaciones",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Configuracion tier.validation
    # -------------------------------------------------------------------------
    _state_field = "movement_state"
    _state_from = ["draft", "assigned"]
    _state_to = ["assigned", "discharged"]
    _cancel_state = "cancelled"
    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        return list(set(super()._get_under_validation_exceptions() + ALWAYS_EDITABLE))

    @api.model
    def _get_after_validation_exceptions(self):
        return list(set(super()._get_after_validation_exceptions() + ALWAYS_EDITABLE))

    @api.model
    def _get_all_validation_exceptions(self):
        return list(set(super()._get_all_validation_exceptions() + ALWAYS_EDITABLE))

    # -------------------------------------------------------------------------
    # Acciones del flujo
    # -------------------------------------------------------------------------

    def action_request_assignment(self):
        """Solicita aprobacion para asignacion institucional o de conductor."""
        self.ensure_one()
        if not self.pending_assignee_id and not self.assigned_person_id:
            raise UserError(
                _("Debe indicar al menos el responsable institucional o el conductor a asignar.")
            )
        self.write({"movement_state": "draft"})
        self._fleet_log_movement("requested")
        return self.request_validation()

    def action_request_reassignment(self):
        """Inicia una reasignacion institucional sin cancelar la asignacion actual."""
        self.ensure_one()
        if not self.pending_assignee_id and not self.assigned_person_id:
            raise UserError(
                _("Debe indicar el nuevo responsable institucional o conductor antes de enviar la solicitud.")
            )
        # Limpiar revisiones anteriores para que need_validation sea True nuevamente.
        if self.review_ids:
            self.review_ids.unlink()
        self._fleet_log_movement("requested")
        return self.request_validation()

    def action_request_discharge(self):
        """Solicita aprobacion para descarga del vehiculo."""
        self.ensure_one()
        if self.review_ids:
            self.review_ids.unlink()
        self.write({"movement_state": "draft"})
        self._fleet_log_movement("requested")
        return self.request_validation()

    def action_cancel_movement(self):
        """Cancela el movimiento en curso."""
        self.ensure_one()
        self.restart_validation()
        self.write({
            "movement_state": "cancelled",
            "pending_assignee_id": False,
        })
        self._fleet_log_movement("cancelled")

    def action_reset_to_draft(self):
        """Reinicia a borrador para una nueva solicitud."""
        self.ensure_one()
        self.restart_validation()
        self.write({"movement_state": "draft"})
        self._fleet_log_movement("restarted")

    def action_accept_driver_change(self):
        """Override del boton nativo: no aplica porque usamos assigned_person_id directamente."""
        return True

    # -------------------------------------------------------------------------
    # Override validate_tier y reject_tier — fuerzan el wizard de comentario
    # -------------------------------------------------------------------------

    def validate_tier(self):
        self.ensure_one()
        return {
            "name": _("Aprobar Movimiento"),
            "type": "ir.actions.act_window",
            "res_model": "fleet.approval.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_vehicle_id": self.id,
                "default_action": "approve",
            },
        }

    def reject_tier(self):
        self.ensure_one()
        return {
            "name": _("Rechazar Movimiento"),
            "type": "ir.actions.act_window",
            "res_model": "fleet.approval.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_vehicle_id": self.id,
                "default_action": "reject",
            },
        }

    # -------------------------------------------------------------------------
    # Logica de transicion tras aprobacion completa
    # -------------------------------------------------------------------------

    def _fleet_apply_approved_state(self):
        """Ejecuta la transicion de estado una vez que todas las revisiones estan aprobadas."""
        self.ensure_one()
        if self.pending_assignee_id:
            # Asignacion/reasignacion institucional — confirmar responsable
            self.with_context(skip_validation_check=True).write({
                "movement_state": "assigned",
                "fleet_responsible_id": self.pending_assignee_id.id,
                "pending_assignee_id": False,
            })
        elif self.movement_state == "draft":
            # Descarga — vehiculo sin asignado pendiente
            self.with_context(skip_validation_check=True).write({"movement_state": "discharged"})
        else:
            # Reasignacion de conductor puro (assigned_person_id ya actualizado)
            self.with_context(skip_validation_check=True).write({"movement_state": "assigned"})

    def _fleet_post_approval_history(self, comment=False):
        """Registra la aprobacion en el historial."""
        self._fleet_log_movement("approved", comment)

    def _fleet_log_movement(self, action, comment=False):
        self.env["fleet.movement.history"].create({
            "vehicle_id": self.id,
            "movement_state": self.movement_state,
            "action": action,
            "done_by": self.env.uid,
            "assignee_id": self.pending_assignee_id.id or self.fleet_responsible_id.id or False,
            "driver_id": self.assigned_person_id.id or False,
            "comment": comment,
        })
