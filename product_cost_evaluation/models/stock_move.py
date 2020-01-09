# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero


class StockMove(models.Model):
    _inherit = 'stock.move'

    company_currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        related='company_id.currency_id',
        store=True,
        string="Company Currency"
    )

    invoice_cost = fields.Monetary(
        compute='compute_invoice_cost',
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        string="Unit Invoice Cost"
    )

    invoice_cost_total = fields.Monetary(
        compute='compute_invoice_cost_total',
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        string="Total Invoice Cost"
    )

    manual_cost = fields.Monetary(
        currency_field='company_currency_id',
        store=True,
        string="Unit Cost"
    )

    manual_cost_total = fields.Monetary(
        compute='compute_manual_cost_total',
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        string="Total Cost"
    )

    purchase_cost = fields.Monetary(
        compute='compute_purchase_cost',
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        string="Unit Purchase Cost"
    )

    purchase_cost_total = fields.Monetary(
        compute='compute_purchase_cost_total',
        currency_field='company_currency_id',
        readonly=True,
        store=True,
        string="Total Purchase Cost"
    )

    quantity_done = fields.Float(
        # Forcing `quantity_done` to be stored so that it can be used to
        # trigger total costs' compute methods
        store=True,
    )

    @api.model
    def create(self, vals):
        # Get `manual_cost` from product's `standard_price`
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['manual_cost'] = product.standard_price
        return super().create(vals)

    @api.multi
    def write(self, vals):
        # Get `manual_cost` from product's `standard_price`
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['manual_cost'] = product.standard_price
        return super().write(vals)

    @api.multi
    def button_edit_manual_cost(self):
        self.ensure_one()
        view = self.env.ref('product_cost_evaluation.edit_manual_cost')
        return {
            'name': _("Edit Manual Cost"),
            'res_id': self.id,
            'res_model': self._name,
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def button_save_manual_cost(self):
        """
        Hook method that allows value to be correctly saved and rendered in
        views
        """
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def button_reset_manual_cost(self):
        """ Restores originale value """
        self.ensure_one()
        self.manual_cost = self._context.get('original_manual_cost') or 0
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    @api.depends(
        'company_currency_id',
        'product_uom',
        'purchase_line_id',
        'purchase_line_id.invoice_lines',
        'purchase_line_id.invoice_lines.currency_id',
        'purchase_line_id.invoice_lines.price_subtotal',
        'purchase_line_id.invoice_lines.quantity',
        'purchase_line_id.invoice_lines.uom_id',
    )
    def compute_invoice_cost(self):
        for sm in self:
            sm.invoice_cost = sm.get_invoice_cost()

    @api.multi
    @api.depends(
        'invoice_cost',
        'quantity_done',
    )
    def compute_invoice_cost_total(self):
        for sm in self:
            sm.invoice_cost_total = sm.get_invoice_cost_total()

    @api.multi
    @api.depends(
        'manual_cost',
        'quantity_done'
    )
    def compute_manual_cost_total(self):
        for sm in self:
            sm.manual_cost_total = sm.get_manual_cost_total()

    @api.multi
    @api.depends(
        'company_currency_id',
        'product_uom',
        'purchase_line_id',
        'purchase_line_id.currency_id',
        'purchase_line_id.price_subtotal',
        'purchase_line_id.product_qty',
        'purchase_line_id.product_uom',
    )
    def compute_purchase_cost(self):
        for sm in self:
            sm.purchase_cost = sm.get_purchase_cost()

    @api.multi
    @api.depends(
        'purchase_cost',
        'quantity_done',
    )
    def compute_purchase_cost_total(self):
        for sm in self:
            sm.purchase_cost_total = sm.get_purchase_cost_total()

    def convert_unit_price(self, unit_price, from_curr, from_uom):
        """
        Unit price's UoM is actually a derived UoM `currency/product UoM`,
        such as `EUR/kg` or `USD/t`.
        This method converts value `unit_price` from original currency
        `from_curr` and UoM `from_uom` to current stock.move
        `company_currency_id` and `product_uom`.
        """
        to_curr, to_uom = self.company_currency_id, self.product_uom
        # Convert by currency (do not round)
        unit_price = from_curr.compute(unit_price, to_curr, round=False)
        # Convert by UoM
        unit_price = from_uom._compute_price(unit_price, to_uom)
        return unit_price

    def get_invoice_cost(self):
        self.ensure_one()
        po_line = self.purchase_line_id
        if not po_line:
            return 0
        inv_lines = po_line.invoice_lines
        if not inv_lines:
            return self.get_purchase_cost()

        invoice_cost = 0
        dp = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure'
        )
        for line in inv_lines.filtered(
            lambda l: not float_is_zero(l.quantity, dp)
        ):
            line_unit_price = line.price_subtotal / line.quantity
            invoice_cost += self.convert_unit_price(
                line_unit_price, line.currency_id, line.uom_id
            )
        return invoice_cost / len(inv_lines)

    def get_invoice_cost_total(self):
        self.ensure_one()
        return self.invoice_cost * self.quantity_done

    def get_manual_cost_total(self):
        self.ensure_one()
        return self.manual_cost * self.quantity_done

    def get_purchase_cost(self):
        self.ensure_one()
        po_line = self.purchase_line_id
        if not po_line:
            return 0
        dp_obj = self.env['decimal.precision']
        account_dp = dp_obj.precision_get('Account')
        uom_dp = dp_obj.precision_get('Product Unit of Measure')
        if float_is_zero(po_line.price_subtotal, account_dp):
            return 0
        elif float_is_zero(po_line.product_qty, uom_dp):
            return 0
        return self.convert_unit_price(
            po_line.price_subtotal / po_line.product_qty,
            po_line.currency_id,
            po_line.product_uom
        )

    def get_purchase_cost_total(self):
        self.ensure_one()
        return self.purchase_cost * self.quantity_done
