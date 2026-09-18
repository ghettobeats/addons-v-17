# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, _


class StockScrap(models.Model):
    _inherit = 'stock.scrap'
    

    state = fields.Selection(selection_add=[
        ('cancel', 'Cancel')])

    def do_scrap(self):
        self._check_company()
        for scrap in self:
            if not scrap.name or scrap.name == 'New':
                scrap.name = self.env['ir.sequence'].next_by_code(
                    'stock.scrap') or _('New')
            move = self.env['stock.move'].create(scrap._prepare_move_values())
            # master: replace context by cancel_backorder
            move.with_context(is_scrap=True)._action_done()
            scrap.write({'move_id': move.id, 'state': 'done'})
            scrap.date_done = fields.Datetime.now()
        return True

    def _check_stock_account_installed(self):
        stock_account_app = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'stock_account')], limit=1)
        if stock_account_app.state != 'installed':
            return False
        else:
            return True

    def action_inventory_scrap_cancel(self):
        for rec in self:
            rec.sudo().mapped('move_id').sudo().write({'state': 'cancel'})
            rec.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'cancel'})

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            rec._sh_unreseve_qty()
            rec.sudo().write({'state': 'cancel'})

    def action_inventory_cancel_scrap_draft(self):
        for rec in self:
            rec.sudo().mapped('move_id').sudo().write({'state': 'draft'})
            rec.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'draft'})
            rec._sh_unreseve_qty()

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            rec.sudo().write({'state': 'draft'})

    def action_inventory_cancel_scrap_delete(self):
        for rec in self:
            rec.sudo().mapped('move_id').sudo().write({'state': 'draft'})
            rec.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'draft'})
            rec._sh_unreseve_qty()

            if rec._check_stock_account_installed():
                # cancel related accouting entries
                account_move = rec.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            rec.sudo().mapped('move_id').sudo().unlink()
            rec.sudo().mapped('move_id').mapped('move_line_ids').sudo().unlink()
            rec.sudo().write({'state': 'draft'})
            rec.sudo().unlink()

    def _sh_unreseve_qty(self):
        # Check qty is not in draft and cancel state
        if self.state not in ['draft', 'cancel']:
            for move_line in self.sudo().mapped('move_id').sudo().mapped('move_line_ids'):
                # unreserve qty
                quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_id.id),
                                                               ('product_id', '=',
                                                                move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id)], limit=1)

                if quant:
                    quant.write(
                        {'quantity': quant.quantity + move_line.qty_done})

                quant = self.env['stock.quant'].sudo().search([('location_id', '=', move_line.location_dest_id.id),
                                                               ('product_id', '=',
                                                                move_line.product_id.id),
                                                               ('lot_id', '=', move_line.lot_id.id)], limit=1)

                if quant:
                    quant.write(
                        {'quantity': quant.quantity - move_line.qty_done})

    def sh_cancel(self):
        if self.company_id.scrap_operation_type == 'cancel':

            self.sudo().mapped('move_id').sudo().write({'state': 'cancel'})
            self.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'cancel'})
            self._sh_unreseve_qty()

            if self._check_stock_account_installed():
                # cancel related accouting entries
                account_move = self.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            self.sudo().write({'state': 'cancel'})

        elif self.company_id.scrap_operation_type == 'cancel_draft':

            self.sudo().mapped('move_id').sudo().write({'state': 'draft'})
            self.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'draft'})
            self._sh_unreseve_qty()

            if self._check_stock_account_installed():
                # cancel related accouting entries
                account_move = self.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            self.sudo().write({'state': 'draft'})

        elif self.company_id.scrap_operation_type == 'cancel_delete':

            self.sudo().mapped('move_id').sudo().write({'state': 'draft'})
            self.sudo().mapped('move_id').mapped(
                'move_line_ids').sudo().write({'state': 'draft'})
            self._sh_unreseve_qty()

            if self._check_stock_account_installed():
                # cancel related accouting entries
                account_move = self.sudo().mapped('move_id').sudo().mapped('account_move_ids')
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
                    'move_id').sudo().mapped('stock_valuation_layer_ids')
                if stock_valuation_layer_ids:
                    stock_valuation_layer_ids.sudo().unlink()

            self.sudo().mapped('move_id').sudo().unlink()
            self.sudo().mapped('move_id').mapped('move_line_ids').sudo().unlink()
            self.sudo().write({'state': 'draft'})
            self.sudo().unlink()

            return {
                'name': 'Stock Scrap',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.scrap',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'target': 'current',
            }
