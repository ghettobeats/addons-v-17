# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class PaySlipReport(models.AbstractModel):
    _name = "report.isjo_hr_payroll.payslip_report"
    _description = "Payslip Report"

    @api.model
    def _get_report_values(self, docids, data={}):
        ###### Test Data #####
        # docids = [3181, 3200, 3250, 3278, 3288]
        ###### Test Data #####
        docs = []
        doc_lines = {}
        docs = self.env['hr.payslip'].browse(docids).sorted(
            lambda r: r.employee_id.department_id.complete_name.lower().replace(' ', ''))
        for doc in docs:
            line_ids = doc.line_ids.filtered(
                lambda r: r.salary_rule_id.appears_on_payslip
            ).sorted(key=lambda r: (r.salary_rule_id.sequence, r.salary_rule_id.name))
            lines = []
            for line in line_ids:
                salary_rule = line.salary_rule_id
                lines.append(dict(
                    category_id_code=line.category_id_code,
                    code=line.code,
                    name=salary_rule.name,
                    quantity=line.quantity,
                    amount=line.amount,
                    total=line.total,
                    column_display_total_on_report=salary_rule.column_display_total_on_report
                ))
            doc_lines[doc.id] = lines

        return dict(
            th_font_size='0.8125rem', # 13px
            font_size='0.6875rem',  # 11px
            footer_font_size='0.5625rem',  # 9px
            hide_footer=True,
            print_duplicate=False,
            docs=docs,
            doc_lines=doc_lines,
        )
