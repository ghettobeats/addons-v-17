# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    @api.model_create_multi
    def create(self, vals_list):
        # A work entry without a work_entry_type_id is always rejected by
        # _check_if_error() and left stuck in the 'conflict' state, even when
        # it doesn't actually overlap anything else (e.g. a line added by hand
        # in the Entradas de trabajo list without filling that field). Default
        # it to "Asistencia"/"Attendance" instead of leaving it undefined.
        default_type = self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)
        if default_type:
            for vals in vals_list:
                if not vals.get('work_entry_type_id'):
                    vals['work_entry_type_id'] = default_type.id
        return super().create(vals_list)
