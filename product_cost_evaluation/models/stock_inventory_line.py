# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    evaluation_id = fields.Many2one(
        'product.cost.evaluation.history',
        string="Purchase Evaluation"
    )

    @api.multi
    def name_get(self):
        names = []
        for line in self:
            prod_name = line.product_id.name_get()[0][-1]
            loc_name = line.inventory_id.name_get()[0][-1]
            names.append((line.id, '{} in {}'.format(prod_name, loc_name)))
        return names

    def get_evaluation_vals(self):
        """
        Prepares values for ``product.cost.evaluation.history`` to be created
        """
        self.ensure_one()

        avg_cost, avg_purchase_cost, avg_error = self.get_average_cost_data()
        fifo_cost, fifo_purchase_cost, fifo_error = self.get_fifo_cost_data()
        lifo_cost, lifo_purchase_cost, lifo_error = self.get_lifo_cost_data()
        list_price, standard_cost, error = self.get_product_cost_data()

        name = ''
        if any([avg_error, fifo_error, lifo_error, error]):
            name = _("Incomplete invoice data")

        return {
            'average_cost': avg_cost,
            'average_purchase_cost': avg_purchase_cost,
            'company_id': self.company_id.id,
            'date_evaluation': self.inventory_id.date,  # todo date_inventory
            'fifo_cost': fifo_cost,
            'fifo_purchase_cost': fifo_purchase_cost,
            'inventory_line_id': self.id,
            'lifo_cost': lifo_cost,
            'lifo_purchase_cost': lifo_purchase_cost,
            'list_price': list_price,
            'location_id': self.inventory_location_id.id,
            'lot_id': self.prod_lot_id.id,
            'name': name,
            'product_id': self.product_id.id,
            'product_qty': self.product_qty,
            'standard_cost': standard_cost,
        }

    def get_average_cost_data(self):
        """
        Computes and returns average cost, average purchase cost, and an error
        flag if any data is missing
        """
        self.ensure_one()

        dp = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )
        avg_cost = purchase_cost = tot_qty = 0
        avg_error = False

        for move_line in self.get_stock_move_lines('average'):
            qty, price_unit, purch_price_unit, err = move_line.get_cost_data()
            if err:
                avg_error = err

            avg_cost += qty * price_unit
            purchase_cost += qty * purch_price_unit
            tot_qty += qty

        if not float_is_zero(tot_qty, dp):
            return avg_cost / tot_qty, purchase_cost / tot_qty, avg_error
        else:
            return 0, 0, avg_error

    def get_fifo_cost_data(self):
        """
        Computes and returns FIFO cost, FIFO purchase cost, and an error flag
        if any data is missing
        """
        self.ensure_one()

        dp = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )
        fifo_cost = purchase_cost = tot_qty = 0
        fifo_error = False
        qty_to_go = self.product_qty

        for move_line in self.get_stock_move_lines('fifo'):
            qty, price_unit, purch_price_unit, err = move_line.get_cost_data()
            if err:
                fifo_error = err

            if float_compare(qty_to_go, qty, dp) >= 0:
                fifo_cost += qty * price_unit
                purchase_cost += qty * purch_price_unit
                tot_qty += qty
                qty_to_go -= qty
            else:
                fifo_cost += qty_to_go * price_unit
                purchase_cost += qty * purch_price_unit
                tot_qty += qty_to_go
                break

        if not float_is_zero(tot_qty, dp):
            return fifo_cost / tot_qty, purchase_cost / tot_qty, fifo_error
        else:
            return 0, 0, fifo_error

    def get_lifo_cost_data(self):
        """
        Computes and returns LIFO cost, LIFO purchase cost, and an error flag
        if any data is missing
        """
        self.ensure_one()

        dp = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )
        lifo_cost = purchase_cost = tot_qty = 0
        lifo_error = False
        qty_to_go = older_qty = self.product_qty

        for move_line in self.get_stock_move_lines('lifo'):
            qty, price_unit, purch_price_unit, err = move_line.get_cost_data()
            if err:
                lifo_error = err

            # Sales
            if move_line.move_id.location_id.usage == 'internal' \
                    and move_line.move_id.location_dest_id.usage != 'internal':
                older_qty += qty

            # Purchases
            if move_line.move_id.location_id.usage != 'internal' \
                    and move_line.move_id.location_dest_id.usage == 'internal':
                older_qty -= qty
                if float_compare(qty_to_go, older_qty, dp) > 0:
                    if float_compare(older_qty, 0, dp) > 0:
                        curr_qty = qty_to_go - older_qty
                        lifo_cost += curr_qty * price_unit
                        purchase_cost += curr_qty * purch_price_unit
                        tot_qty += curr_qty
                        qty_to_go = older_qty
                    else:
                        lifo_cost += qty_to_go * price_unit
                        purchase_cost += qty * purch_price_unit
                        tot_qty += qty_to_go
                        break

        if not float_is_zero(tot_qty, dp):
            return lifo_cost / tot_qty, purchase_cost / tot_qty, lifo_error
        else:
            return 0, 0, lifo_error

    def get_product_cost_data(self):
        """ Returns default product data """
        self.ensure_one()
        return self.product_id.lst_price, self.product_id.standard_price, False

    def get_stock_move_lines(self, mode):
        self.ensure_one()
        if mode in ('average', 'fifo'):
            return self.env['stock.move.line'].search(
                [('lot_id', '=', self.prod_lot_id.id),
                 ('move_id.company_id', '=', self.company_id.id),
                 ('move_id.date', '<=', self.inventory_id.date),  # todo date_inventory
                 ('move_id.location_dest_id.usage', '=', 'internal'),
                 ('move_id.location_id.usage', '!=', 'internal'),
                 ('move_id.product_id', '=', self.product_id.id),
                 ('move_id.state', '=', 'done')],
                order='date desc, id desc'
            )
        elif mode == 'lifo':
            return self.env['stock.move.line'].search(
                [('lot_id', '=', self.prod_lot_id.id),
                 ('move_id.company_id', '=', self.company_id.id),
                 ('move_id.date', '<=', self.inventory_id.date),  # todo date_inventory
                 '|',
                 ('move_id.location_dest_id.usage', '=', 'internal'),
                 ('move_id.location_id.usage', '=', 'internal'),
                 ('move_id.product_id', '=', self.product_id.id),
                 ('move_id.state', '=', 'done')],
                order='date desc, id desc'
            )
        raise ValidationError(
            _("Invalid mode '{}' for evaluation.").format(mode)
        )

    def set_evaluation(self):
        self.ensure_one()
        evaluation_obj = self.env['product.cost.evaluation.history']
        evaluation_vals = self.get_evaluation_vals()
        self.evaluation_id = evaluation_obj.create(evaluation_vals)
