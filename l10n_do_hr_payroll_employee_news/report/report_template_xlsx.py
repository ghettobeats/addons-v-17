# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import models
# from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
#     FORMATS,
#     XLS_HEADERS,
# )
from odoo.exceptions import UserError

_logget = logging.getLogger(__name__)


class ReportTemplateXlsx(models.AbstractModel):
    _name = 'report.payroll_report.template_xlsx'
    # _inherit = 'report.report_xlsx.abstract'
    _description = 'Reporte de Nomina XLS'

    def _get_ws_params(self, wb, data, run_ids):
        theader_custom = wb.add_format({'border': True, 'border_color': '#D3D3D3',
                                        'bold': True, 'bg_color': '#FFFFCC',
                                        'text_wrap': True, 'valign': 'vcenter'})

        theader_custom_right = wb.add_format({'border': True, 'border_color': '#D3D3D3',
                                              'bold': True, 'bg_color': '#FFFFCC',
                                              'text_wrap': True, 'valign': 'vcenter', 'align': 'right'})

        ids = data.get("run_ids")  # self.env.context.get('run_ids')

        query = '''
          select distinct l.code, l.name, s.sequence
          from hr_payslip_line l, hr_salary_rule s
          where l.salary_rule_id = s.id and slip_id in (
            select id from hr_payslip where payslip_run_id in %s)
          and l.total > 0 and s.appears_on_report
          order by s.sequence;
        '''
        self.env.cr.execute(query, (tuple(ids),))

        cols = self.env.cr.fetchall()

        _template = {}
        for i in cols:
            line = "line.get('%s')" % i[0]
            formula = 'formula.get("%s")' % i[0]
            _template[i[0]] = {
                'header': {
                    'value': i[1],
                    'format': theader_custom_right,
                },
                'data': {
                    'value': self._render(line),
                    'format': FORMATS['format_amount_right'],

                },
                'width': 14,
                'total': {
                    'value': self._render(formula),
                    'format': FORMATS['format_amount_right'],
                    'type': 'formula'
                }
            }

        rule_template = {
            'employee_name': {
                'header': {
                    'value': 'Empleado',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['employee_name']"),
                },
                'width': 33,
                'total': {
                    'value': 'TOTAL',
                }
            },
            'num_document': {
                'header': {
                    'value': 'Cedula',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['num_document']"),
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            }, 'wage': {
                'header': {
                    'value': 'Salario',
                    'format': theader_custom_right,
                },
                'data': {
                    'value': self._render("line['wage']"),
                    'format': FORMATS['format_tcell_amount_right_bold'],

                },
                'width': 14,
                'total': {
                    'value': self._render("formula.get('wage')"),
                }
            }, 'department': {
                'header': {
                    'value': 'Departamento',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['department_id']['name']"),
                    'format': FORMATS['format_amount_right']
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            }, 'job': {
                'header': {
                    'value': 'Puesto de Trab.',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['job_id']['name']"),
                    'format': FORMATS['format_amount_right']
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            }, 'contract': {
                'header': {
                    'value': 'Contrato',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['contract']"),
                    'format': theader_custom,
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            }
        }

        rule_template.update(_template)

        codes = [col[0] for col in cols]

        hidden = data.get("hidden", [])  # self.env.context.get('hidden', [])
        extra = list(set(['num_document', 'department', 'job', 'wage']) - set(hidden))

        wanted_list = ['employee_name'] + sorted(extra) + codes
        company = self.env.company.name
        ws_params = {
            'ws_name': 'Nomina',
            'generate_ws_method': 'generate_report',
            'title': '%s - Reporte de Nomina' % company,
            'wanted_list': wanted_list,
            'rules': codes,
            'col_specs': rule_template,
        }

        return [ws_params]

    def _get_ws_params_extra(self):

        _template = {
            'name': {
                'header': {
                    'value': 'Nomina(s)',
                },
                'data': {
                    'value': self._render("line"),

                },
                'width': 33,
            },
        }

        wanted_list = ['name']

        ws_params = {
            'wanted_list': wanted_list,
            'col_specs': _template,
        }

        return ws_params

    def generate_report(self, workbook, ws, ws_params, data, run_ids):

        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])

        self._set_column_width(ws, ws_params)


        row_pos = 4


        payslip_run_ids = self.env['hr.payslip.run'].browse(data.get('run_ids'))
        nominas = ', '.join([r.name for r in payslip_run_ids])
        ws.write('B1', ws_params.get('title'), FORMATS['format_ws_title'])
        ws.write('B3', 'Nomina(s)', FORMATS['format_theader_yellow_left'])
        ws.write('B4', nominas)

        row_pos += 1
        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='header',
            default_format=FORMATS['format_theader_yellow_left'])

        ws.set_row(row_pos - 1, 30)
        # ws.freeze_panes(row_pos, 1)

        lines = data.get("lines", {}).values()  # self.env.context['lines'].values()

        for data_dict in lines:
            # raise UserError(str(data_dict))
            if isinstance(data_dict["job_id"]["name"], dict):
                data_dict["job_id"]["name"] = data_dict["job_id"]["name"]["es_DO"]
            row_pos = self._write_line(
                ws, row_pos, ws_params, col_specs_section='data',
                render_space={
                    'line': data_dict,
                },
            )

        len_records = len(lines)
        rules_formula = {}
        for rule in ws_params['rules']:
            pos = ws_params['wanted_list'].index(rule)

            start = self._rowcol_to_cell(row_pos - len_records, pos)
            stop = self._rowcol_to_cell(row_pos - 1, pos)
            formula = '=SUM(%s:%s)' % (start, stop)
            rules_formula[rule] = formula

        row_pos = self._write_line(
            ws, row_pos, ws_params, col_specs_section='total',
            render_space={
                'formula': rules_formula,
            },
            default_format=FORMATS['format_tcell_amount_right'])

        groupby_department = True
        if groupby_department:
            ws = workbook.add_worksheet('Por_Departamentos')
            ws.set_portrait()
            ws.fit_to_pages(1, 0)
            ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
            ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])

            self._set_column_width(ws, ws_params)


            row_pos = 4

            payslip_run_ids = self.env['hr.payslip.run'].browse(self.env.context.get('run_ids'))
            nominas = ', '.join([r.name for r in payslip_run_ids])
            ws.write('B1', ws_params.get('title'), FORMATS['format_ws_title'])
            ws.write('B3', 'Nomina(s)', FORMATS['format_theader_yellow_left'])
            ws.write('B4', nominas)
            data_groupby = data.get('data_groupby', [])

            for dep, vals in data_groupby.items():

                row_pos = self._write_ws_title(ws, row_pos, {'title': dep})
                row_pos -= 1
                row_pos = self._write_line(
                    ws, row_pos, ws_params, col_specs_section='header',
                    default_format=FORMATS['format_theader_yellow_left'])

                for lines in vals:
                    if isinstance(lines["job_id"]["name"], dict):
                        lines["job_id"]["name"] = lines["job_id"]["name"]["es_DO"]
                    row_pos = self._write_line(
                        ws, row_pos, ws_params, col_specs_section='data',
                        render_space={
                            'line': lines,
                        },
                    )

                len_records = len(vals)
                rules_formula = {}
                for rule in ws_params['rules']:
                    pos = ws_params['wanted_list'].index(rule)

                    start = self._rowcol_to_cell(row_pos - len_records, pos)
                    stop = self._rowcol_to_cell(row_pos - 1, pos)
                    formula = '=SUM(%s:%s)' % (start, stop)
                    rules_formula[rule] = formula

                row_pos = self._write_line(
                    ws, row_pos, ws_params, col_specs_section='total',
                    render_space={
                        'formula': rules_formula,
                    },
                    default_format=FORMATS['format_tcell_amount_right'])

                row_pos += 2
