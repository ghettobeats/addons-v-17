# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################

from odoo import fields, models


class IsjoTerminatedOfficersReport(models.Model):
    _name = 'isjo.terminated.officers.report'
    _description = 'Oficiales Desvinculados'
    _auto = False
    _order = 'x_departure_date desc'
    _rec_name = 'x_employee_name'

    x_cod_card           = fields.Char(string='Código',            readonly=True)
    x_employee_name      = fields.Char(string='Empleado',          readonly=True)
    x_cedula             = fields.Char(string='Cédula',            readonly=True)
    x_gender             = fields.Char(string='Género',            readonly=True)
    x_fecha_nacimiento   = fields.Char(string='Fecha Nacimiento',  readonly=True)
    x_departure_date     = fields.Date(string='_departure_date',   readonly=True)
    x_fecha_cese         = fields.Char(string='Fecha de Cese',     readonly=True)
    x_motivo_salida      = fields.Char(string='Motivo de Salida',  readonly=True)
    x_mes_cese           = fields.Char(string='Mes de Cese',       readonly=True)
    x_ano_cese           = fields.Integer(string='Año de Cese',    readonly=True)
    x_dias_desde_cese    = fields.Integer(string='Días desde Cese', readonly=True)
    x_fecha_inicio_contrato = fields.Char(string='Inicio Contrato', readonly=True)
    x_fecha_ingreso      = fields.Char(string='Fecha de Ingreso',  readonly=True)
    x_dias_trabajados    = fields.Integer(string='Días Trabajados', readonly=True)
    x_anos_antiguedad    = fields.Integer(string='Años Antigüedad', readonly=True)
    x_department_name    = fields.Char(string='Departamento',      readonly=True)
    x_puesto             = fields.Char(string='Puesto',            readonly=True)
    x_estado_empleado    = fields.Char(string='Estado',            readonly=True)
    x_clase              = fields.Char(string='Clase',             readonly=True)
    x_region             = fields.Char(string='Región',            readonly=True)
    x_zona               = fields.Char(string='Zona',              readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS isjo_terminated_officers_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW isjo_terminated_officers_report AS (
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
                    e.departure_date                                AS x_departure_date,
                    TO_CHAR(e.departure_date, 'DD/MM/YYYY')        AS x_fecha_cese,
                    dr.name->>'es_DO'                               AS x_motivo_salida,
                    CASE TRIM(TO_CHAR(e.departure_date, 'Month'))
                        WHEN 'January'   THEN 'Enero'
                        WHEN 'February'  THEN 'Febrero'
                        WHEN 'March'     THEN 'Marzo'
                        WHEN 'April'     THEN 'Abril'
                        WHEN 'May'       THEN 'Mayo'
                        WHEN 'June'      THEN 'Junio'
                        WHEN 'July'      THEN 'Julio'
                        WHEN 'August'    THEN 'Agosto'
                        WHEN 'September' THEN 'Setiembre'
                        WHEN 'October'   THEN 'Octubre'
                        WHEN 'November'  THEN 'Noviembre'
                        ELSE                  'Diciembre'
                    END                                             AS x_mes_cese,
                    EXTRACT(YEAR FROM e.departure_date)::int        AS x_ano_cese,
                    (CURRENT_DATE - e.departure_date)::int          AS x_dias_desde_cese,
                    TO_CHAR(c.date_start, 'DD/MM/YYYY')            AS x_fecha_inicio_contrato,
                    TO_CHAR(first_c.first_date, 'DD/MM/YYYY')      AS x_fecha_ingreso,
                    (e.departure_date - first_c.first_date)::int    AS x_dias_trabajados,
                    EXTRACT(YEAR FROM age(e.departure_date, first_c.first_date))::int
                                                                    AS x_anos_antiguedad,
                    d.name->>'es_DO'                                AS x_department_name,
                    j.name->>'es_DO'                                AS x_puesto,
                    CASE
                        WHEN e.active = false AND e.departure_date IS NOT NULL THEN 'Cesado'
                        WHEN e.active = false THEN 'Inactivo'
                        ELSE 'Activo'
                    END                                             AS x_estado_empleado,
                    sc.name                                         AS x_clase,
                    r.name                                          AS x_region,
                    z.name                                          AS x_zona
                FROM hr_employee e
                LEFT JOIN hr_departure_reason dr ON e.departure_reason_id = dr.id
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
                    e.active = FALSE
                    AND e.departure_date IS NOT NULL
                ORDER BY e.departure_date DESC, e.name
            )
        """)
