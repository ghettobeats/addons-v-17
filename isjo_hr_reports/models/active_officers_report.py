# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################

from odoo import fields, models


class IsjoActiveOfficersReport(models.Model):
    _name = 'isjo.active.officers.report'
    _description = 'Oficiales Activos por Día'
    _auto = False
    _order = 'x_date desc'
    _rec_name = 'x_employee_name'

    # ── Identificación ───────────────────────────────────────────────────────
    x_cod_card           = fields.Char(string='Código',            readonly=True)
    x_employee_name      = fields.Char(string='Empleado',          readonly=True)
    x_cedula             = fields.Char(string='Cédula',            readonly=True)
    x_gender             = fields.Char(string='Género',            readonly=True)
    x_fecha_nacimiento   = fields.Char(string='Fecha Nacimiento',  readonly=True)

    # ── Contrato / Ingreso ───────────────────────────────────────────────────
    x_date               = fields.Date(string='_date',             readonly=True)
    x_fecha_ingreso      = fields.Char(string='Fecha de Ingreso',  readonly=True)
    x_fecha_inicio_contrato = fields.Char(string='Inicio Contrato', readonly=True)
    x_dias_antiguedad    = fields.Integer(string='Días de Antigüedad', readonly=True)
    x_anos_antiguedad    = fields.Integer(string='Años Antigüedad', readonly=True)

    # ── Organización ─────────────────────────────────────────────────────────
    x_department_name    = fields.Char(string='Departamento',      readonly=True)
    x_puesto             = fields.Char(string='Puesto',            readonly=True)
    x_clase              = fields.Char(string='Clase',             readonly=True)
    x_region             = fields.Char(string='Región',            readonly=True)
    x_zona               = fields.Char(string='Zona',              readonly=True)

    # ── Estado ───────────────────────────────────────────────────────────────
    x_estado_empleado    = fields.Char(string='Estado',            readonly=True)
    x_vigencia           = fields.Char(string='Vigencia',          readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS isjo_active_officers_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW isjo_active_officers_report AS (
                SELECT
                    e.id                                            AS id,
                    e.emp_id                                        AS x_cod_card,
                    UPPER(e.name)                                   AS x_employee_name,
                    e.identification_id                             AS x_cedula,
                    CASE
                        WHEN e.gender = 'male' THEN 'Masculino'
                        ELSE 'Femenino'
                    END                                             AS x_gender,
                    TO_CHAR(e.birthday, 'DD/MM/YYYY')              AS x_fecha_nacimiento,
                    first_c.first_date                              AS x_date,
                    TO_CHAR(first_c.first_date, 'DD/MM/YYYY')      AS x_fecha_ingreso,
                    TO_CHAR(c.date_start, 'DD/MM/YYYY')            AS x_fecha_inicio_contrato,
                    (CURRENT_DATE - first_c.first_date)::int        AS x_dias_antiguedad,
                    EXTRACT(YEAR FROM age(CURRENT_DATE, first_c.first_date))::int
                                                                    AS x_anos_antiguedad,
                    d.name->>'es_DO'                                AS x_department_name,
                    j.name->>'es_DO'                                AS x_puesto,
                    sc.name                                         AS x_clase,
                    r.name                                          AS x_region,
                    z.name                                          AS x_zona,
                    'Activo - Vigente'                              AS x_estado_empleado,
                    'VIGENTE'                                       AS x_vigencia
                FROM hr_employee e
                LEFT JOIN LATERAL (
                    SELECT id, employee_id, date_start, job_id, department_id
                    FROM hr_contract
                    WHERE employee_id = e.id
                    ORDER BY date_start DESC
                    LIMIT 1
                ) c ON TRUE
                LEFT JOIN (
                    SELECT employee_id, MIN(date_start) AS first_date
                    FROM hr_contract
                    GROUP BY employee_id
                ) first_c ON e.id = first_c.employee_id
                LEFT JOIN hr_department       d  ON d.id  = c.department_id
                LEFT JOIN hr_job              j  ON j.id  = c.job_id
                LEFT JOIN hr_region           r  ON r.id  = e.region_id
                LEFT JOIN hr_zone             z  ON z.id  = e.zone_id
                LEFT JOIN hr_structure_class  sc ON sc.id = e.structure_class_id
                WHERE
                    e.active = TRUE
                ORDER BY e.name
            )
        """)
