from odoo import models, fields, api


class HrPayslipRun(models.Model):
    _name = "hr.payslip.run"
    _inherit = ["hr.payslip.run", "mail.thread", "mail.activity.mixin"]

    gov_txt_file = fields.Binary(
        string="Origin file", required=False, attachment=True, filters="*.txt",
    )
    gov_txt_file_name = fields.Char()

    @api.multi
    def close_payslip_run(self):
        for payslip_run in self:
            for payslip in payslip_run.slip_ids:
                if payslip.state == "draft":
                    payslip.action_payslip_done()
        return super(HrPayslipRun, self).close_payslip_run()
