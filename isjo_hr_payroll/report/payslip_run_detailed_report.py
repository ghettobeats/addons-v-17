# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
import babel
from datetime import datetime, time
from functools import reduce


class PaySlipRunDetailedReport(models.AbstractModel):
    _name = "report.isjo_hr_payroll.payslip_run_datailed_report"
    _description = "Payslip Batch Detailed Report"

    @api.model
    def _get_report_values(self, docids, data={}):
        ###### Test Data #####
        # data.update(dict(sorted_by='area'))
        # docids = [17]
        ###### Test Data #####
        show_summary = True  # parameter to show the summary by department
        docs = []
        doc_lines = {}
        summary = []
        total_by_lines = dict()
        employer_contrib_sum_lines = dict()
        salary_rules_sum_lines = dict()
        provision_sum_lines = dict()
        employer_contrib_total = 0
        net_wages_total = 0
        line_group = 'payroll'
        lines_by_group = \
            dict(employer_contribution=dict(code=['TCDE001'], category_code=['CODEMTSS']),
                 provision=dict(code=['PROREPA', 'PROVA'], category_code=[]))
        payslip_batch = self.env['hr.payslip.run'].browse(docids)
        docs = payslip_batch.slip_ids.sorted(
            key=lambda r: (r.employee_id.name))
        date_from = payslip_batch.date_start.strftime('%d-%m-%Y')
        date_to = payslip_batch.date_end.strftime('%d-%m-%Y')
        report_subtitle = '<span class="pr-3">Período de Pago:</span><span><span class="font-weight-bold secondary-color">Desde</span> - %s - <span class="font-weight-bold secondary-color">Hasta</span> - %s<span>' % \
            (date_from, date_to)
        department_ids = self.env['hr.department'].search([], order='name')
        department_summary = {
            dept.id: dict(id=dept.id,
                          parent_name=dept.parent_id.name or '',
                          complete_name=dept.complete_name,
                          name=dept.name,
                          color=dept.color,
                          lines=dict())
            for dept in department_ids}
        for doc in docs:
            lines = []
            basic_salary = 0
            # fetch all slip lines
            line_ids = self.env['hr.payslip.line'].search([('slip_id', '=', doc.id)]).sorted(
                key=lambda r: (r.salary_rule_id.sequence, r.salary_rule_id.name))
            emp_department = doc.employee_id.department_id
            if not emp_department.id:
                raise UserError(
                    f'El empleado "{doc.employee_id.name}" no tiene asignado el departamento al que pertenece.')
            summary = department_summary[emp_department.id]
            summary_lines = summary['lines']
            for line in line_ids:
                salary_rule = line.salary_rule_id
                line_group = 'payroll'

                for key, item in lines_by_group.items():
                    if line.code in item['code'] or line.category_id_code in item['category_code']:
                        line_group = key
                        break
                if not salary_rule.id in total_by_lines:
                    total_by_lines[salary_rule.id] = \
                        dict(name=salary_rule.name,
                             code=line.code,
                             sequence=salary_rule.sequence,
                             category_id_code=line.category_id_code,
                             total=line.total,
                             appears_on_payslip=salary_rule.appears_on_payslip,
                             line_group=line_group)
                else:
                    total_by_lines[salary_rule.id]['total'] += line.total

                if salary_rule.appears_on_payslip:
                    lines.append(dict(name=salary_rule.name,
                                      code=line.code,
                                      category_id_code=line.category_id_code,
                                      column_display_total_on_report=salary_rule.column_display_total_on_report,
                                      quantity=line.quantity,
                                      amount=line.amount,
                                      total=line.total))
                if line.code == 'NET':  # Salario Neto Devengado
                    net_wages_total += line.total
                if not salary_rule.id in summary_lines:
                    summary_lines[salary_rule.id] = \
                        dict(name=salary_rule.name,
                             code=line.code,
                             sequence=salary_rule.sequence,
                             category_id_code=line.category_id_code,
                             total=line.total,
                             appears_on_payslip=line.appears_on_payslip,
                             line_group=line_group)
                else:
                    summary_lines[salary_rule.id]['total'] += line.total
            doc_lines[doc.id] = lines

        docs = docs.sorted(
            lambda r: r.employee_id.department_id.complete_name.lower().replace(' ', ''))
        if show_summary:
            total_by_lines = \
                sorted(total_by_lines.values(), key=lambda r: r['sequence'])
            department_summary = \
                sorted([item for item in department_summary.values() if len(item['lines'].keys()) > 0],
                       key=lambda r: r['complete_name'].lower().replace(' ', ''))
        else:
            department_summary = []
        return dict(
            report_title=f'{"Nómina para Fines de Revisión" if payslip_batch.state == "draft" else "Nómina Cerrada"} - {payslip_batch.name}',
            report_subtitle=report_subtitle,
            # font_size='0.8125rem',  # = 13px
            font_size='0.78125rem',  # = 12.5px
            payslip_batch_name=payslip_batch.name,
            show_summary=show_summary,
            # show_net_wages_for_validate=True,
            docs=docs,
            doc_lines=doc_lines,
            total_by_lines=total_by_lines,
            department_summary=department_summary,
            net_wages_total=net_wages_total
        )
