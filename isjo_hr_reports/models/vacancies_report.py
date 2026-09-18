from odoo import fields, models


class IsjoVacanciesReport(models.Model):
    _name = 'isjo.vacancies.report'
    _description = 'Vacantes por Cubrir'
    _auto = False
    _order = 'x_vacancies desc'
    _rec_name = 'x_job_name'

    # TODO: definir campos con Daniel

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS isjo_vacancies_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW isjo_vacancies_report AS (
                SELECT 1 AS id
            )
        """)
