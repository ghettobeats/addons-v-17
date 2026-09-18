import json
from odoo import fields, http
from odoo.http import request

class HolidayControllers(http.Controller):
    @http.route('/publicholiday_calendar_datepicker/get_holidays', auth='public', type='http', methods=['GET'])
    def get_public_holidays(self):
        user = request.env.user
        holidays = request.env['resource.calendar.leaves'].sudo().search([('resource_id', '=', False)])
        return request.make_response(
            data=json.dumps([{'date': str(h.date_from)} for h in holidays]),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/publicholiday_calendar_datepicker/is_holiday', type='http', auth='public', website=True)
    def is_holiday(self, event_id):
        holiday_id = request.env['resource.calendar.leaves'].sudo().search(
            [('meeting_id', '=', int(event_id)), ('resource_id', '=', False)], limit=1)
        return request.make_response(
            data=json.dumps(bool(holiday_id)),
            headers=[('Content-Type', 'application/json')]
        )
