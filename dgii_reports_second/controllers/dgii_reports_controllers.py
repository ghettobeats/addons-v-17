#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from werkzeug.utils import redirect
from odoo.http import request, Controller, route
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response
from werkzeug.urls import url_encode, url_decode, iri_to_uri



import json
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools import image_process, topological_sort, html_escape, pycompat, ustr, apply_inheritance_specs, lazy_property
from odoo.addons.web.controllers.main import ReportController


class DgiiReportsControllers(Controller):

    @route(['/dgii_reports_second/<ncf_rnc>'], type='http', auth='user')
    def redirect_link(self, ncf_rnc):

        env = request.env
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')

        if str(ncf_rnc)[:1] == 'B' or str(ncf_rnc)[:1] == 'E':
            invoice_id = env['account.move'].search([
                ('ref', '=', ncf_rnc),
                ('move_type', 'in', ('out_invoice', 'in_invoice','out_refund','in_refund'))
                ], limit=1)
            if invoice_id:
                # Get action depending on invoice type
                action_map = {
                    'out_invoice': request.env.ref(
                        'account.action_move_out_invoice_type'
                        ),
                    'in_invoice': request.env.ref(
                        'account.action_move_in_invoice_type'
                        ),
                    'out_refund': request.env.ref(
                        'account.action_move_out_invoice_type'
                        ),
                    'in_refund': request.env.ref(
                        'account.action_move_in_invoice_type'
                        )
                }
                action = action_map[invoice_id.move_type]
                url = "%s/web#id=%s&action=%s&model=account.move&view" \
                      "_type=form" % (base_url, invoice_id.id, action.id)
                return redirect(url)  # Returns invoice form view

            return redirect(base_url)

        else:
            partner_id = env['res.partner'].search([('vat', '=', ncf_rnc)],
                                                   limit=1)
            if partner_id:

                url = "%s/web#id=%s&model=res.partner&view_type=form" % (
                    base_url, partner_id.id)
                return redirect(url)  # Returns partner form view

            return redirect(base_url)



class CustomReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token, context=None):
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = json.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type == 'qweb-pdf' else 'text'
                extension = 'pdf' if type == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = dict(url_decode(url.split('?')[1]).items())  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                custom_report_name = False
                if 'options' in data:
                    for rec,k in json.loads(data['options']).items():

                        if 'report_file_name' in rec:
                            custom_report_name = k

                filename = "%s.%s" % (report.name if custom_report_name == False else custom_report_name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",")]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))