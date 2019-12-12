# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models
from odoo.tools.float_utils import float_is_zero


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def get_cost_data(self):
        self.ensure_one()

        move = self.move_id
        default_uom = move.product_id.uom_id
        qty = move.product_uom._compute_quantity(self.qty_done, default_uom)
        price_unit, purch_price_unit, err = 0, 0, False
        dp = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )

        # Get cost data from purchase line
        if move.purchase_line_id:
            po_line = move.purchase_line_id
            if not po_line.invoice_lines:
                err = True
            else:
                inv_lines = po_line.invoice_lines.filtered(
                    lambda x: x.invoice_id.state in ['open', 'paid']
                )
                price_subtotal = sum(l.price_subtotal for l in inv_lines)
                qty_subtotal = sum(l.quantity for l in inv_lines)
                if not float_is_zero(qty_subtotal, dp):
                    price_unit = price_subtotal / qty_subtotal

            if not float_is_zero(po_line.product_qty, dp):
                purch_price_unit = po_line.price_subtotal / po_line.product_qty

        return qty, price_unit, purch_price_unit, err
