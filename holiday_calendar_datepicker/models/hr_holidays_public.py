from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def write(self, vals):
        holiday_ids = self.env['resource.calendar.leaves'].search(
            [('meeting_id', '=', self.id), ('resource_id', '=', False)])
        if holiday_ids:
            users_obj = self.env['res.users']
            access_meeting = False
            for user in users_obj.search([]):
                if user.has_group("base.user_admin"):
                    if self.env.uid == user.id:
                        access_meeting = True
                        break
            if access_meeting:
                return super(CalendarEvent, self).write(vals)
            raise AccessError(_('Only Admin Can Change Holiday Meetings.'))
        return super(CalendarEvent, self).write(vals)


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    meeting_id = fields.Many2one("calendar.event", string="Meeting", copy=False)

    def _prepare_holidays_meeting_values(self):
        self.ensure_one()
        categ_id = self.env.ref("holiday_calendar_datepicker.event_type_holiday", False)
        users = self.env['res.users'].search([('partner_id', '!=', False)])
        partner_ids = [user.partner_id.id for user in users]
        meeting_values = {
            "name": (
                "{}".format(self.name if self.name else 'Holiday')
            ),
            "start": self.date_from,
            "stop": self.date_from,
            "allday": True,
            "privacy": "public",
            'partner_ids': [(4, pid, False) for pid in partner_ids],
            "show_as": "busy",
        }
        if categ_id:
            meeting_values.update({"categ_ids": [(6, 0, categ_id.ids)]})
        return meeting_values

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for record in res:
            record.meeting_id = self.env["calendar.event"].create(
                record._prepare_holidays_meeting_values()
            )
        return res

    def write(self, vals):
        date_from = vals.get('date_from', False)
        if date_from:
            self.meeting_id.start = date_from
            self.meeting_id.stop = date_from
        return super(ResourceCalendarLeaves, self).write(vals)

    def unlink(self):
        self.mapped("meeting_id").sudo().unlink()
        return super().unlink()
