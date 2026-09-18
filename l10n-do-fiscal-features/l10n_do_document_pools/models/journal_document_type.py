#  Copyright (c) 2022 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

import pytz
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


def get_l10n_do_datetime():
    """
    Multipurpose Dominican Republic local datetime
    """

    # *-*-*-*-*- Remove this comment *-*-*-*-*-*
    # Because an user can use a distinct timezone,
    # this method ensure that DR localtime stuff like
    # auto expire Fiscal Sequence by its date works,
    # no matter server/client date.

    date_now = datetime.now()
    return pytz.timezone("America/Santo_Domingo").localize(date_now)


class AccountJournalDocumentType(models.Model):
    _name = "l10n_do.account.journal.document_type"
    _rec_name = "l10n_latam_document_type_id"
    _inherit = [
        "l10n_do.account.journal.document_type",
        "mail.thread",
        "mail.activity.mixin",
    ]

    auth_number = fields.Char(
        "Authorization number",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("valid", "Valid"),
            ("depleted", "Depleted"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )
    sequence_start = fields.Integer(
        tracking=True,
        default=1,
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    sequence_end = fields.Integer(
        tracking=True,
        default=1,
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_do_ncf_expiration_date = fields.Date(
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    queued_pool_ids = fields.One2many(
        "account.journal.document_type.queued_pool",
        "journal_document_type_id",
        string="Queued Document Pools",
    )
    active_pool_id = fields.Many2one(
        "account.journal.document_type.queued_pool",
        string="Active Document",
        copy=False,
    )
    l10n_do_next_sequence = fields.Integer(
        "Next Document Sequence",
        compute="_compute_l10n_do_next_sequence",
    )
    l10n_do_ncf_type = fields.Selection(
        related="l10n_latam_document_type_id.l10n_do_ncf_type"
    )
    l10n_do_first_sequence = fields.Boolean(
        "First sequence",
        default=True,
        help="Technical field to indicate if invoice is going "
        "to take first sequence from journal document type.",
    )
    l10n_do_sequence_remaining = fields.Integer(
        string="Remaining",
        compute="_compute_l10n_do_sequence_remaining",
    )
    active = fields.Boolean("Active", default=True, tracking=True)

    @api.depends("sequence_end", "l10n_do_next_sequence")
    def _compute_l10n_do_sequence_remaining(self):
        for sequence in self:
            sequence.l10n_do_sequence_remaining = (
                sequence.sequence_end - sequence.l10n_do_next_sequence + 1
            )

    @api.depends("l10n_latam_document_type_id", "l10n_do_ncf_type", "sequence_start")
    def _compute_l10n_do_next_sequence(self):
        for doc_type in self:

            if doc_type.l10n_do_first_sequence:
                doc_type.l10n_do_next_sequence = doc_type.sequence_start
            else:
                document_type = self.env["l10n_latam.document.type"]
                doc_type_map = document_type.get_l10n_do_document_type_mapping()
                tax_payer_type_map = document_type.get_l10n_do_tax_payer_type_mapping()
                Move = self.env["account.move"]
                partner = self.env["res.partner"].new(
                    {
                        "name": "dummy",
                        "l10n_do_dgii_tax_payer_type": tax_payer_type_map[
                            doc_type.l10n_do_ncf_type
                        ],
                    }
                )
                move_type = doc_type_map[doc_type.l10n_do_ncf_type]
                move = Move.new(
                    {
                        "move_type": move_type,
                        "partner_id": partner.id,
                        "journal_id": Move.with_context(
                            default_move_type=move_type
                        )._get_default_journal(),
                    }
                )
                raw_last_sequence = move.with_context(
                    is_l10n_do_seq=True, next_sequence=True
                )._get_last_sequence()
                last_sequence = int(raw_last_sequence[-8:]) if raw_last_sequence else 0
                doc_type.l10n_do_next_sequence = last_sequence + 1 or 1

    def action_confirm(self):
        self.ensure_one()
        msg = _(
            "Are you sure want to confirm this Fiscal Sequence? "
            "Once you confirm this Fiscal Sequence cannot be edited."
        )
        action = self.env.ref(
            "l10n_do_document_pools.ir_sequence_validate_wizard_action"
        ).read()[0]
        action["context"] = {
            "default_name": msg,
            "default_journal_document_type_id": self.id,
            "action": "confirm",
        }
        return action

    def action_cancel(self):
        self.ensure_one()
        msg = _(
            "Are you sure want to cancel this Fiscal Sequence? "
            "Once you cancel this Fiscal Sequence cannot be used."
        )
        action = self.env.ref(
            "l10n_do_document_pools.ir_sequence_validate_wizard_action"
        ).read()[0]
        action["context"] = {
            "default_name": msg,
            "default_journal_document_type_id": self.id,
            "action": "cancel",
        }
        return action

    def _action_confirm(self):
        for rec in self:
            # Use DR local time
            l10n_do_date = get_l10n_do_datetime().date()
            rec.state = "expired" if l10n_do_date >= rec.l10n_do_ncf_expiration_date else "valid"

    def _action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
            if rec.active_pool_id and rec.active_pool_id.state == "active":
                rec.active_pool_id.state = "cancelled"

    def _expire_sequences(self):
        """
        Function called from ir.cron that check all active sequence
        expiration_date and set state = expired if necessary
        """
        # Use DR local time
        l10n_do_date = get_l10n_do_datetime().date()
        fiscal_sequence_ids = self.search([("state", "=", "valid")])

        expired = fiscal_sequence_ids.filtered(
            lambda s: l10n_do_date >= s.l10n_do_ncf_expiration_date
            and s.l10n_do_ncf_type not in ("e-consumer", "consumer")
        )
        expired.write({"state": "expired"})
        queued_pool_ids = expired.mapped("queued_pool_ids")
        queued_pool_ids.write({"state": "expired"})

    def _get_queued_pool(self):
        queued_pool_id = self.env["account.journal.document_type.queued_pool"].search(
            [
                ("state", "=", "queue"),
                ("journal_document_type_id", "=", self.id),
            ],
            order="sequence_end asc",
            limit=1,
        )
        return queued_pool_id

    def _get_document_type_starting_sequence(self):
        self.ensure_one()
        return str(self.sequence_start - 1).zfill(
            10
            if str(self.l10n_latam_document_type_id.l10n_do_ncf_type).startswith("e-")
            else 8
        )


class DocumentTypeQueuedPool(models.Model):
    _name = "account.journal.document_type.queued_pool"
    _description = "Sequence Queued Document Pool"
    _order = "expiration_date desc"

    name = fields.Char(
        string="Authorization number",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    expiration_date = fields.Date(
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=fields.Date.end_of(
            fields.Date.today().replace(year=fields.Date.today().year + 1), "year"
        ),
    )
    sequence_start = fields.Integer(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=1,
        copy=False,
    )
    sequence_end = fields.Integer(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=1,
        copy=False,
    )
    journal_document_type_id = fields.Many2one(
        "l10n_do.account.journal.document_type",
        string="Journal Document Type",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queue", "Queued"),
            ("active", "Active"),
            ("depleted", "Depleted"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        copy=False,
    )
    l10n_do_ncf_type = fields.Selection(
        related="journal_document_type_id.l10n_latam_document_type_id.l10n_do_ncf_type"
    )

    @api.model
    def default_get(self, fields):
        res = super(DocumentTypeQueuedPool, self).default_get(fields)

        ctx = self.env.context
        if "params" in ctx and "id" in ctx["params"]:
            journal_document_type_id = self.env[
                "l10n_do.account.journal.document_type"
            ].browse(ctx["params"]["id"])
            sequence_start = journal_document_type_id.sequence_end + 1
            res.update(
                {
                    "sequence_start": sequence_start,
                    "sequence_end": sequence_start,
                }
            )

        return res

    @api.constrains("state")
    def _validate_active(self):
        if len(self.filtered(lambda s: s.state == "active")) > 1:
            raise UserError(_("Cannot have multiple active sequence at once"))

    @api.constrains(
        "sequence_start", "sequence_end", "state", "journal_document_type_id"
    )
    def _validate_sequence_range(self):
        for rec in self.filtered(lambda s: s.state != "cancelled"):
            if any(
                [True for value in [rec.sequence_start, rec.sequence_end] if value <= 0]
            ):
                raise UserError(_("Sequence values must be greater than zero."))
            if rec.sequence_start >= rec.sequence_end:
                raise UserError(_("End sequence must be greater than start sequence."))
            domain = [
                ("sequence_end", ">=", rec.sequence_start),
                ("sequence_start", "<=", rec.sequence_end),
                ("state", "in", ("active", "queue")),
                ("journal_document_type_id", "=", rec.journal_document_type_id.id),
                ("id", "!=", rec.id),
            ]
            if self.search_count(domain):
                raise UserError(_("You cannot use another Fiscal Sequence range."))

    def action_queue(self):
        self.ensure_one()
        # Use DR local time
        l10n_do_date = get_l10n_do_datetime().date()

        if l10n_do_date >= self.expiration_date:
            self.state = "expired"
        elif self.journal_document_type_id.state != "valid":
            self._start_queued_pool()
        else:
            self.state = "queue"

    def action_cancel(self):
        self.ensure_one()
        self.state = "cancelled"
        if self.journal_document_type_id.active_pool_id == self:
            self.journal_document_type_id.state = "cancelled"

    def _start_queued_pool(self):
        self.ensure_one()

        self.state = "active"
        self.journal_document_type_id.write(
            {
                "auth_number": self.name,
                "active_pool_id": self.id,
                "sequence_end": self.sequence_end,
                "l10n_do_ncf_expiration_date": self.expiration_date,
                "sequence_start": self.sequence_start,
                "l10n_do_first_sequence": True,
            }
        )
        self.journal_document_type_id._action_confirm()
