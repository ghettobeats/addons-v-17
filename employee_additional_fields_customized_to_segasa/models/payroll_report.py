# -*- coding: utf-8 -*-

from itertools import chain

from odoo import models
from odoo.addons.report_xlsx_helper.report.report_xlsx_format import FORMATS, XLS_HEADERS


class ReportTemplateXlsx(models.AbstractModel):
    _inherit = 'report.payroll_report.template_xlsx'

    def _get_ws_params(self, wb, data, run_ids):
        ws_params = super(ReportTemplateXlsx, self)._get_ws_params(wb, data, run_ids)[0]
        rule_template = ws_params["col_specs"]
        wanted_list = ws_params["wanted_list"]
        
        theader_custom = wb.add_format({'border': True, 'border_color': '#D3D3D3',
                          'bold': True, 'bg_color': '#FFFFCC',
                          'text_wrap': True, 'valign': 'vcenter', 'align': 'left'})

        rule_template.update({
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
                    'value': f"{len(data['lines'])} Empleado(s)",
                }
            },
            'num_document': {
                'header': {
                    'value': 'Código',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['identification_code']"),
                },
                'width': 14,
                'total': {
                    'value': 'TOTAL',
                }
            },
            "identification": {
                'header': {
                    'value': 'Cédula',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['identification'] or ''"),
                    'format': FORMATS['format_amount_right'],
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            },
            "zone": {
                'header': {
                    'value': 'Zona',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['zone'] or ''"),
                    'format': FORMATS['format_amount_right'],
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            },
            "region": {
                'header': {
                    'value': 'Región',
                    'format': theader_custom,
                },
                'data': {
                    'value': self._render("line['region'] or ''"),
                    'format': FORMATS['format_amount_right'],
                },
                'width': 14,
                'total': {
                    'value': '',
                }
            },
        })

        idx = [i for i, val in enumerate(wanted_list) if val == "employee_name"][0]
        wanted_list.insert(idx+1, "identification")
        wanted_list.insert(idx+2, "region")
        wanted_list.insert(idx+3, "zone")

        if "num_document" in wanted_list:
            wanted_list.remove("num_document")
            wanted_list.insert(0, "num_document")

        ws_params["col_specs"] = rule_template
        ws_params["wanted_list"] = wanted_list

        return [ws_params]
     
    
    def generate_report(self, workbook, ws, ws_params, data, run_ids):
        super().generate_report(workbook, ws, ws_params, data, run_ids)
        inputs = data["lines"][next(iter(data["lines"]))]["inputs"]
        
        if not inputs:
            return

        headers = ["Código", "Empleado", "Cédula", "Región", "Zona", "Departamento"] 
        totals = [0] * len(inputs)
        
        row_pos = len(data["lines"]) + 10
        ws.write_row(row_pos, 0, headers, cell_format=FORMATS['format_theader_yellow_left'])
        
        start = len(headers)
        for i, header in enumerate(inputs):
            ws.merge_range(row_pos-1, start + i*3, row_pos-1, start + i*3+2, header,
                           cell_format=FORMATS['format_theader_yellow_center'])
            ws.write_row(row_pos, start + i*3, ["Cantidad", "Tasa", "Importe"],
                         cell_format=FORMATS['format_theader_yellow_center'])
                
        for key, line in data["lines"].items():
            row_pos += 1
            cols = [line["identification_code"] or "",
                    line["employee_name"] or "",
                    line["identification"] or "",
                    line["region"] or "",
                    line["zone"] or "",
                    line["department_id"]["name"] or ""]
            ws.write_row(row_pos, 0, cols)

            rates = [(f"{(total/amount):.2f}" if amount != 0 else "")
                     for total, amount in zip(line["amounts"], line["hours"])]
            input_cols = chain(*(zip(line["hours"], rates, line["amounts"])))
            ws.write_row(row_pos, start, list(input_cols),
                         cell_format=FORMATS["format_amount_right"])

        totals = {
            "hours": [sum(line["hours"]) for _, line in data["lines"].items()],
            "amounts": [sum(line["amounts"]) for _, line in data["lines"].items()],
            "rates":  [""] * len(data["lines"]),
        }
        total_cols = chain(*zip(totals["hours"], totals["rates"], totals["amounts"]))
        
        ws.write_row(row_pos+1, 0, ["TOTAL"], cell_format=FORMATS["format_right"])
        ws.write_row(row_pos+1, start, list(total_cols), cell_format=FORMATS["format_amount_right"])
        

class WizardPayslipReportXlsx(models.TransientModel):
    _inherit = 'wizard.payroll_report.xlsx'

    def _get_payslip_inputs(self, run_ids):
        inputs = []
        payslips = self.env["hr.payslip"].search([("payslip_run_id", "in", run_ids)])
        for slip in payslips:
            inputs += [line.input_type_id.name for line in slip.input_line_ids if line.amount > 0]
        return set(inputs)
    
    def _get_data(self, run_ids):
        data_lines = super(WizardPayslipReportXlsx, self)._get_data(run_ids)
        hr_employee = self.env["hr.employee"]
        hr_payslip = self.env["hr.payslip"]
        inputs = self._get_payslip_inputs(run_ids)
        
        for id in data_lines:
            employee = hr_employee.search([("name", "=", data_lines[id]["employee_name"])], limit=1)
            payslips = hr_payslip.search([("employee_id", "=", employee.id), ("payslip_run_id", "in", run_ids)])
            hours = []
            amounts = []
            
            for input_type in inputs:
                input_type_id = self.env["hr.payslip.input.type"].search([("name", "=", input_type)], limit=1)
                input_lines = self.env["hr.payslip.input"].search([("id", "in", payslips.input_line_ids._ids),
                                                                   ("input_type_id", "=", input_type_id.id)])
                line_ids = self.env["hr.payslip.line"].search([("id", "in", payslips.line_ids._ids)])
                
                if input_lines and [line for line in line_ids if line.name in input_type]:
                    hours.append(sum(line.amount for line in input_lines))
                    amounts.append(sum(line.total for line in line_ids))
                else:
                    hours.append(0)
                    amounts.append(0)
            
            data_lines[id].update({
                "identification": employee.identification_id,
                "identification_code": employee.identification_code,
                "zone": employee.zone_id.name,
                "region": dict(hr_employee._fields["region"]._description_selection(self.env)).get(employee.region),
                # --
                "hours": hours,
                "amounts": amounts,
                "inputs": list(inputs)
            })

        return data_lines
