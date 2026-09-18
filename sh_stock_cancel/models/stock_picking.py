# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models


class Picking(models.Model):
    _inherit = 'stock.picking'

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock_account')], limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    def action_picking_cancel(self):
        for rec in self:
            if rec.sudo().mapped('move_ids_without_package'):
                rec._sh_unreseve_qty()
                rec.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'cancel'})
                rec.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                # rec._sh_unreseve_qty()

                if rec._check_stock_account_installed():

                    # cancel related accouting entries
                    account_move = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()

                    # cancel stock valuation
                    stock_valuation_layer_ids = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()

            rec.sudo().write({'state': 'cancel'})

    def action_picking_cancel_draft(self):
        for rec in self:
            if rec.sudo().mapped('move_ids_without_package'):
                rec._sh_unreseve_qty()
                rec.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                # rec._sh_unreseve_qty()

                if rec._check_stock_account_installed():
                    # cancel related accouting entries
                    account_move = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()
                        
                    # cancel stock valuation
                    stock_valuation_layer_ids = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()

            rec.sudo().write({'state': 'draft'})

    def action_picking_cancel_delete(self):
        for rec in self:
            if rec.sudo().mapped('move_ids_without_package'):

                rec._sh_unreseve_qty()
                rec.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                rec.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                if rec._check_stock_account_installed():
                    # cancel related accouting entries
                    account_move = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()
            
                    # cancel stock valuation
                    stock_valuation_layer_ids = rec.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()
            
                rec.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().unlink()
                rec.sudo().mapped('move_ids_without_package').sudo().unlink()
            
            rec.sudo().write({'state': 'draft', 'show_mark_as_todo': True})
            rec.sudo().unlink()
       

    def _sh_unreseve_qty(self):
        for move_line in self.sudo().mapped('move_ids_without_package').mapped('move_line_ids'):
            
            # Check qty is not in draft and cancel state
            if self.state not in ['draft','cancel','assigned','waiting'] :
                
                # unreserve qty
                quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                               ('product_id', '=',
                                                                move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id)], limit=1)
    
                if quant:
                    quant.write({'quantity': quant.quantity + move_line.qty_done})
    
                quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                               ('product_id', '=',
                                                                move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id)], limit=1)
    
                if quant:
                    quant.write({'quantity': quant.quantity - move_line.qty_done})

    def sh_cancel(self):

        if self.company_id.picking_operation_type == 'cancel':
            if self.sudo().mapped('move_ids_without_package'):
                self._sh_unreseve_qty()
                self.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'cancel'})
                self.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'cancel'})
                # self._sh_unreseve_qty()

                if self._check_stock_account_installed():
                    # cancel related accouting entries
                    account_move = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()

                    # cancel stock valuation
                    stock_valuation_layer_ids = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()

            self.sudo().write({'state': 'cancel'})

        elif self.company_id.picking_operation_type == 'cancel_draft':
            if self.sudo().mapped('move_ids_without_package'):
                self._sh_unreseve_qty()
                self.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                self.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                # self._sh_unreseve_qty()

                if self._check_stock_account_installed():
                    # cancel related accouting entries
                    account_move = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()

                    # cancel stock valuation
                    stock_valuation_layer_ids = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()

            self.sudo().write({'state': 'draft'})

        elif self.company_id.picking_operation_type == 'cancel_delete':
            if self.sudo().mapped('move_ids_without_package'):
                self._sh_unreseve_qty()
                self.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                self.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
                # self._sh_unreseve_qty()

                if self._check_stock_account_installed():
                    # cancel related accouting entries
                    account_move = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('account_move_ids')
                    account_move_line_ids = account_move.sudo().mapped('line_ids')
                    reconcile_ids = []
                    if account_move_line_ids:
                        reconcile_ids = account_move_line_ids.sudo().mapped('id')
                    reconcile_lines = self.env['account.partial.reconcile'].sudo().search(
                        ['|', ('credit_move_id', 'in', reconcile_ids), ('debit_move_id', 'in', reconcile_ids)])
                    if reconcile_lines:
                        reconcile_lines.sudo().unlink()
                    account_move.mapped(
                        'line_ids.analytic_line_ids').sudo().unlink()
                    account_move.sudo().write({'state': 'draft', 'name': '/'})
                    account_move.sudo().with_context(
                        {'force_delete': True}).unlink()

                    # cancel stock valuation
                    stock_valuation_layer_ids = self.sudo().mapped(
                        'move_ids_without_package').sudo().mapped('stock_valuation_layer_ids')
                    if stock_valuation_layer_ids:
                        stock_valuation_layer_ids.sudo().unlink()

                self.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().unlink()
                self.sudo().mapped('move_ids_without_package').sudo().unlink()

            self.sudo().write({'state': 'draft', 'show_mark_as_todo': True})
            self.sudo().unlink()

            return {
                'name': 'Inventory Transfer',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'view_type': 'form',
                'view_mode': 'tree,kanban,form',
                'target': 'current',
            }
