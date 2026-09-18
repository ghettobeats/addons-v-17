# -*- coding: utf-8 -*-
#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields


class ProductCategory(models.Model):
    _name = 'product.category'
    _inherit = ['product.category', 'mail.thread']

    commission = fields.Boolean('Can generate commission entries', track_visibility='onchange',
                                help="Check this field if products with this category can generate commission entries "
                                     "for invoices Salesperson")
    percentage = fields.Float(track_visibility='onchange')
    fixed_amount = fields.Float(track_visibility='onchange')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    commission_ok = fields.Boolean('Can commission', default=True, track_visibility='onchange')
    percentage = fields.Float(track_visibility='onchange')
    fixed_amount = fields.Float(track_visibility='onchange')
