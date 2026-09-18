# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################

from odoo import fields, models


class IsjoStaffRotationReport(models.Model):
    _name = 'isjo.staff.rotation.report'
    _description = 'Rotación de Personal'
    _auto = False
    _order = 'x_fecha_movimiento desc'
    _rec_name = 'x_employee_name'

    # ── Empleado ─────────────────────────────────────────────────────────────
    x_cod_card          = fields.Char(string='Código',              readonly=True)
    x_employee_name     = fields.Char(string='Empleado',            readonly=True)
    x_cedula            = fields.Char(string='Cédula',              readonly=True)
    x_gender            = fields.Char(string='Género',              readonly=True)

    # ── Movimiento ────────────────────────────────────────────────────────────
    x_tipo_movimiento   = fields.Selection([
        ('ingreso',  'Ingreso'),
        ('salida',   'Salida'),
    ], string='Tipo de Movimiento', readonly=True)
    x_fecha_movimiento  = fields.Date(string='_fecha',              readonly=True)
    x_fecha_mov_str     = fields.Char(string='Fecha',               readonly=True)
    x_mes_movimiento    = fields.Char(string='Mes',                 readonly=True)
    x_ano_movimiento    = fields.Char(string='Año',                 readonly=True)
    x_motivo_salida     = fields.Char(string='Motivo de Salida',    readonly=True)

    # ── Organización ─────────────────────────────────────────────────────────
    x_department_name   = fields.Char(string='Departamento',        readonly=True)
    x_puesto            = fields.Char(string='Puesto',              readonly=True)
    x_clase             = fields.Char(string='Clase',               readonly=True)
    x_region            = fields.Char(string='Región',              readonly=True)
    x_zona              = fields.Char(string='Zona',                readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS isjo_staff_rotation_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW isjo_staff_rotation_report AS (

                -- INGRESOS: empleados con contrato iniciado
                SELECT
                    e.id * 2 - 1                                    AS id,
                    e.emp_id                                        AS x_cod_card,
                    UPPER(e.name)                                   AS x_employee_name,
                    e.identification_id                             AS x_cedula,
                    CASE WHEN e.gender = 'male' THEN 'Masculino' ELSE 'Femenino' END
                                                                    AS x_gender,
                    'ingreso'                                       AS x_tipo_movimiento,
                    c.date_start                                    AS x_fecha_movimiento,
                    TO_CHAR(c.date_start, 'DD/MM/YYYY')            AS x_fecha_mov_str,
                    CASE TRIM(TO_CHAR(c.date_start, 'Month'))
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
                    END                                             AS x_mes_movimiento,
                    TO_CHAR(c.date_start, 'YYYY')                  AS x_ano_movimiento,
                    NULL                                            AS x_motivo_salida,
                    d.name->>'es_DO'                                AS x_department_name,
                    j.name->>'es_DO'                                AS x_puesto,
                    sc.name                                         AS x_clase,
                    r.name                                          AS x_region,
                    z.name                                          AS x_zona
                FROM hr_employee e
                JOIN LATERAL (
                    SELECT date_start, department_id, job_id
                    FROM hr_contract
                    WHERE employee_id = e.id
                    ORDER BY date_start ASC
                    LIMIT 1
                ) c ON TRUE
                LEFT JOIN hr_department      d  ON d.id  = c.department_id
                LEFT JOIN hr_job             j  ON j.id  = c.job_id
                LEFT JOIN hr_structure_class sc ON sc.id = e.structure_class_id
                LEFT JOIN hr_region          r  ON r.id  = e.region_id
                LEFT JOIN hr_zone            z  ON z.id  = e.zone_id

                UNION ALL

                -- SALIDAS: empleados desvinculados
                SELECT
                    e.id * 2                                        AS id,
                    e.emp_id                                        AS x_cod_card,
                    UPPER(e.name)                                   AS x_employee_name,
                    e.identification_id                             AS x_cedula,
                    CASE WHEN e.gender = 'male' THEN 'Masculino' ELSE 'Femenino' END
                                                                    AS x_gender,
                    'salida'                                        AS x_tipo_movimiento,
                    e.departure_date                                AS x_fecha_movimiento,
                    TO_CHAR(e.departure_date, 'DD/MM/YYYY')        AS x_fecha_mov_str,
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
                    END                                             AS x_mes_movimiento,
                    TO_CHAR(e.departure_date, 'YYYY')              AS x_ano_movimiento,
                    dr.name->>'es_DO'                               AS x_motivo_salida,
                    d.name->>'es_DO'                                AS x_department_name,
                    j.name->>'es_DO'                                AS x_puesto,
                    sc.name                                         AS x_clase,
                    r.name                                          AS x_region,
                    z.name                                          AS x_zona
                FROM hr_employee e
                LEFT JOIN hr_departure_reason dr ON dr.id = e.departure_reason_id
                JOIN LATERAL (
                    SELECT date_start, department_id, job_id
                    FROM hr_contract
                    WHERE employee_id = e.id
                    ORDER BY date_start DESC
                    LIMIT 1
                ) c ON TRUE
                LEFT JOIN hr_department      d  ON d.id  = c.department_id
                LEFT JOIN hr_job             j  ON j.id  = c.job_id
                LEFT JOIN hr_structure_class sc ON sc.id = e.structure_class_id
                LEFT JOIN hr_region          r  ON r.id  = e.region_id
                LEFT JOIN hr_zone            z  ON z.id  = e.zone_id
                WHERE e.active = FALSE
                  AND e.departure_date IS NOT NULL

                ORDER BY x_fecha_movimiento DESC
            )
        """)
