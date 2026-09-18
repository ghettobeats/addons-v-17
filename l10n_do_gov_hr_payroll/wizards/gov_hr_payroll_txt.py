# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta


class GovHrPayrollTxt(models.TransientModel):
    _name = "gov.hr.payroll.txt"
    _description = "Create payroll from txt"

    def _default_structure(self):
        return self.env.ref("l10n_do_gov_hr_payroll.hr_payroll_gov_structure_base").id

    def _default_journal(self):
        journal_obj = self.env["account.journal"].search(
            [("is_for_payroll", "=", True)], limit=1
        )
        if journal_obj:
            return journal_obj.id
        return False

    txt_binary = fields.Binary(
        string="TXT file",
        required=True,
        filters="*.txt",
        help="File extention Must be TXT file",
    )
    txt_binary_name = fields.Char()
    struct_id = fields.Many2one(
        comodel_name="hr.payroll.structure",
        string="Structure",
        required=True,
        default=_default_structure,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        domain=[("is_for_payroll", "=", True)],
        default=_default_journal,
    )

    def generate_payroll(self):
        file_content = base64.decodestring(self.txt_binary)
        file_content = file_content.decode("latin-1")
        file_lines = file_content.split("\r\n")
        date_str = file_lines[0][150:156]
        date_start = (
            fields.Date.to_string(datetime.strptime(date_str + "01", "%Y%m%d").date()),
        )
        date_end = (
            fields.Date.to_string(
                (
                    datetime.strptime(date_str + "01", "%Y%m%d").date()
                    + relativedelta(months=+1, day=1, days=-1)
                )
            ),
        )

        payslip_run_obj = self.env["hr.payslip.run"].create(
            {
                "name": _("Payroll: %s") % date_str,
                "gov_txt_file": self.txt_binary,
                "gov_txt_file_name": self.txt_binary_name,
                "date_start": date_start,
                "date_end": date_end,
                "journal_id": self.journal_id.id,
            }
        )
        employees_creates = []
        departments_creates = []
        jobs_creates = []
        contracts_creates = []

        for line in file_lines:
            record_type = line[:1]

            if record_type in ("A", "D"):

                # TODO: REMOVE BLANK SPACE after name
                employee_id = line[139:150]
                employee_name = line[43:79]
                job_name = line[79:109]
                department_name = line[281:320]
                contract_name = line[422:433]
                salary = self._get_amount(line[158:175])

                # Analityc features
                analytic_account_code = line[449:459]
                analytic_tag_name = (
                    line[13:15] + line[15:17] + line[17:19] + line[19:23]
                )

                analytic_account_obj = self.env["account.analytic.account"].search(
                    [("code", "=", analytic_account_code)], limit=1
                )
                if not analytic_account_obj:
                    raise UserError(
                        _("The analytical account with the code %s does not exist")
                        % (analytic_account_code)
                    )

                analytic_tags_obj = self.env["account.analytic.tag"].search(
                    [("name", "like", analytic_tag_name)], limit=1
                )
                if not analytic_tags_obj:
                    raise UserError(
                        _("The analytical tag with the name %s does not exist")
                        % (analytic_tag_name)
                    )

                employee = self._get_employee(
                    employee_id, employee_name, job_name, department_name
                )
                employee_obj = employee.get("employee_obj")
                if employee.get("employee_create"):
                    employees_creates.append(employee_obj)
                if employee.get("department_create"):
                    departments_creates.append(employee_obj.department_id)
                if employee.get("job_create"):
                    jobs_creates.append(employee_obj.job_id)
                contract = self._get_contract(
                    employee_obj,
                    contract_name,
                    salary,
                    analytic_account_obj,
                    analytic_tags_obj,
                )
                contract_obj = contract.get("contract_obj")
                if contract.get("contract_create"):
                    contracts_creates.append(contract_obj)
                payslip_obj = self._get_payslip(
                    employee_obj,
                    contract_obj,
                    payslip_run_obj,
                    analytic_account_obj,
                    analytic_tags_obj,
                    date_start,
                    date_end,
                )

            if record_type == "A":

                # TODO: validate total discount

                # Profits amounts
                amount_base = self._get_amount(line[158:175])
                input_code = "BASIC"
                input_name = _("Basic Salary")
                self._create_input(payslip_obj, input_name, input_code, amount_base)

                amount_incentive = self._get_amount(line[175:192])
                input_code = "INC"
                input_name = _("Incentive")
                self._create_input(
                    payslip_obj, input_name, input_code, amount_incentive
                )

                amount_others = self._get_amount(line[192:209])
                input_code = "OREM"
                input_name = _("Others remunerations")
                self._create_input(payslip_obj, input_name, input_code, amount_others)

                amount_gross = self._get_amount(line[209:226])
                input_code = "GROSS"
                input_name = _("Gross")
                self._create_input(payslip_obj, input_name, input_code, amount_gross)

                amount_net = self._get_amount(line[243:260]) + self._get_amount(
                    line[260:277]
                )
                input_code = "NET"
                input_name = _("Net Salary")
                self._create_input(payslip_obj, input_name, input_code, amount_net)

                # Contribution amounts:
                amount_afp = self._get_amount(line[354:371])
                input_code = "SVDSC"
                input_name = _(u"Contribución - Fondo de Pensiones (AFP/SVDS)")
                self._create_input(payslip_obj, input_name, input_code, amount_afp)

                amount_srl = self._get_amount(line[371:388])
                input_code = "SRLC"
                input_name = _(u"Contribución - Seguro de Riesgos Laborales (SRL)")
                self._create_input(payslip_obj, input_name, input_code, amount_srl)

                amount_sfs = self._get_amount(line[388:405])
                input_code = "SFSC"
                input_name = _(u"Contribución - Seguro Familiar de Salud (SFS)")
                self._create_input(payslip_obj, input_name, input_code, amount_sfs)

                amount_pension = self._get_amount(line[405:422])
                input_code = "SVDSA"
                input_name = _(u"Contribución - Fondo de Pensiones Adicional")
                self._create_input(payslip_obj, input_name, input_code, amount_pension)

            if record_type == "D":

                input_code = line[35:43]
                input_name = "".join([i for i in line[109:139] if not i.isdigit()])
                salary_rule = self.env["hr.salary.rule"].search(
                    [
                        ("code", "=", input_code),
                        ("id", "in", self.struct_id.rule_ids._ids),
                    ]
                )

                if not salary_rule:
                    raise UserError(
                        _(
                            "The %s salary rule does not exist in salairal structure "
                            "%s, please create it and assign it to the salary structure"
                        )
                        % (input_name, self.struct_id.name)
                    )

                amount = -1 * (self._get_amount(line[209:226]))
                self._create_input(payslip_obj, input_name, input_code, amount)

        for payslip in payslip_run_obj.slip_ids:
            payslip.compute_sheet()

        if len(employees_creates) != 0:
            message = "<ul>%s" % (_("A new employee was created:"))
            for employee in employees_creates:
                message += "<ul><li><a target='_blank' href='%s'>%s</a></li>" % (
                    "/web#id=%s&view_type=form&model=hr.employee" % (employee.id,),
                    employee.name,
                )
                message += "</ul>"
            message += "</ul>"
            payslip_run_obj.message_post(body=message)

        if len(departments_creates) != 0:
            message = "<ul>%s" % (_("A new department was created:"))
            for department in departments_creates:
                message += "<ul><li><a target='_blank' href='%s'>%s</a></li>" % (
                    "/web#id=%s&view_type=form&model=hr.department" % (department.id,),
                    department.name,
                )
                message += "</ul>"
            message += "</ul>"
            payslip_run_obj.message_post(body=message)

        if len(jobs_creates) != 0:
            message = "<ul>%s" % (_("A new job title was created:"))
            for job in jobs_creates:
                message += "<ul><li><a target='_blank' href='%s'>%s</a></li>" % (
                    "/web#id=%s&view_type=form&model=hr.job" % (job.id,),
                    job.name,
                )
                message += "</ul>"
            message += "</ul>"
            payslip_run_obj.message_post(body=message)

        if len(contracts_creates) != 0:
            message = "<ul>%s" % (_("A new contract was created:"))
            for contract in contracts_creates:
                message += "<ul><li><a target='_blank' href='%s'>%s</a></li>" % (
                    "/web#id=%s&view_type=form&model=hr.contract" % (contract.id,),
                    contract.name,
                )
                message += "</ul>"
            message += "</ul>"
            payslip_run_obj.message_post(body=message)

        return {
            "name": _("Payslip Batch"),
            "view_mode": "form",
            "res_model": "hr.payslip.run",
            "type": "ir.actions.act_window",
            "res_id": payslip_run_obj.id,
        }

    def _get_employee(self, employee_id, employee_name, job_name, department_name):
        """
        If employee doesn't exist, create employee, department and job title.
        :param employee_id:
        :param employee_name:
        :param job_name:
        :return: hr.employee obj
        """
        employee_obj = self.env["hr.employee"].search(
            [("identification_id", "=", employee_id)], limit=1
        )
        employee_create = False
        department_create = False
        job_create = False

        if not employee_obj:

            employee_obj = self.env["hr.employee"].create(
                {"name": employee_name, "identification_id": employee_id}
            )
            employee_create = True

        department_obj = employee_obj.department_id

        if not department_obj:

            department_obj = self.env["hr.department"].search(
                [("name", "=", department_name)]
            )
            if not department_obj:
                department_obj = self.env["hr.department"].create(
                    {"name": department_name}
                )
                department_create = True
            employee_obj.write({"department_id": department_obj.id})

        if not employee_obj.job_id:
            job_obj = self.env["hr.job"].search([("name", "=", job_name)])
            if not job_obj:
                job_obj = self.env["hr.job"].create(
                    {"name": job_name, "department_id": department_obj.id}
                )
                job_create = True
            employee_obj.write({"job_id": job_obj.id})

        return {
            "employee_obj": employee_obj,
            "department_create": department_create,
            "job_create": job_create,
            "employee_create": employee_create,
        }

    def _get_contract(
        self,
        employee_obj,
        contract_name,
        salary,
        analytic_account_obj,
        analytic_tags_obj,
    ):
        """
        If contract doesn't exist, create it
        :param employee_obj:
        :return: hr.contract obj
        """
        contract_obj = self.env["hr.contract"].search(
            [("employee_id", "=", employee_obj.id), ("state", "=", "open")], limit=1
        )
        contract_create = False

        if not contract_obj:
            contract_obj = self.env["hr.contract"].create(
                {
                    "name": _("Contract: %s %s") % (employee_obj.name, contract_name),
                    "struct_id": self.struct_id.id,
                    "employee_id": employee_obj.id,
                    "job_id": employee_obj.job_id.id,
                    "department_id": employee_obj.department_id.id,
                    "state": "open",
                    "wage": salary,
                    "analytic_account_id": analytic_account_obj.id,
                    "analytic_tag_ids": [(6, 0, analytic_tags_obj.ids)],
                }
            )
            contract_create = True

        return {
            "contract_obj": contract_obj,
            "contract_create": contract_create,
        }

    def _get_payslip(
        self,
        employee_obj,
        contract_obj,
        payslip_run_obj,
        analytic_account_obj,
        analytic_tags_obj,
        date_start,
        date_end,
    ):
        """
        If payslip for this payslip_run doesn't exist, create it
        :param employee_obj:
        :param contract_obj:
        :param payslip_run_obj:
        :return: hr.payslip obj
        """
        payslip_obj = self.env["hr.payslip"].search(
            [
                ("employee_id", "=", employee_obj.id),
                ("id", "in", payslip_run_obj.slip_ids._ids),
            ]
        )

        if not payslip_obj:
            payslip_obj = self.env["hr.payslip"].create(
                {
                    "employee_id": employee_obj.id,
                    "payslip_run_id": payslip_run_obj.id,
                    "contract_id": contract_obj.id,
                    "struct_id": self.struct_id.id,
                    "journal_id": self.journal_id.id,
                    "analytic_account_id": analytic_account_obj.id,
                    "analytic_tag_ids": [(6, 0, analytic_tags_obj.ids)],
                    "date_from": date_start,
                    "date_to": date_end,
                }
            )

        return payslip_obj

    def _get_amount(self, amount_str):
        """
        Convert str len = 17 to float amount
        :param amount_str:
        :return: float_amount
        """
        integer = float(amount_str[:15])
        decimal = float(amount_str[15:]) / 100
        float_amount = integer + decimal
        return float_amount

    def _create_input(self, payslip_obj, input_name, input_code, amount):

        # TODO: confirm if input exist on payslip
        self.env["hr.payslip.input"].create(
            {
                "name": input_name,
                "code": "I" + input_code,
                "contract_id": payslip_obj.contract_id.id,
                "payslip_id": payslip_obj.id,
                "amount": amount,
            }
        )
