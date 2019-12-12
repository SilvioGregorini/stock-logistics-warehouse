# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductCostEvaluationHistory(models.Model):
    _name = 'product.cost.evaluation.history'
    _description = "Product Cost Evaluation History"

    @api.model
    def get_default_company_id(self):
        return self.env.user.company_id

    average_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="Avg Weighted Product Unit Cost",
    )

    average_purchase_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="Avg Weighted Product Unit Purchase Cost",
    )

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
        string="Company Currency",
    )

    company_id = fields.Many2one(
        'res.company',
        default=get_default_company_id,
        string="Company",
    )

    date_evaluation = fields.Date(
        string="Evaluation Date",
    )

    # TODO: fefo management
    # fefo_cost = fields.Monetary(
    #     string="FEFO product unit cost',
    # )

    fifo_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="FIFO Product Unit Cost",
    )

    fifo_purchase_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="FIFO Product Unit Purchase Cost",
    )

    inventory_id = fields.Many2one(
        'stock.inventory',
        readonly=True,
        related='inventory_line_id.inventory_id',
        store=True,
        string="Inventory"
    )

    inventory_line_id = fields.Many2one(
        'stock.inventory.line',
        string="Inventory Line",
    )

    lifo_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="LIFO Product Unit Cost",
    )

    lifo_purchase_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="LIFO Product Unit Purchase Cost",
    )

    list_price = fields.Monetary(
        currency_field='company_currency_id',
        string="Standard Product Price",
    )

    location_id = fields.Many2one(
        'stock.location',
        string="Stock Location",
    )

    lot_id = fields.Many2one(
        'stock.production.lot',
        ondelete='restrict',
        string="Lot/Serial Number",
    )

    name = fields.Text(
        string="Name",
    )

    product_id = fields.Many2one(
        'product.product',
        string="Product",
    )

    product_qty = fields.Float(
        string="Quantity",
    )

    product_qty_uom = fields.Many2one(
        'product.uom',
        string="UOM",
    )

    # TODO: real value management
    real_value = fields.Monetary(
        currency_field='company_currency_id',
        help="If manually set, it is used in report instead of every other"
             " value.",
        string="Real market value",
    )

    standard_cost = fields.Monetary(
        currency_field='company_currency_id',
        string="Standard Product Unit Cost",
    )

    @api.multi
    def name_get(self):
        names = []
        for eva in self:
            prod_name = eva.product_id.name_get()[0][-1]
            loc_name = eva.location_id.name_get()[0][-1]
            date = fields.Date.from_string(eva.date_evaluation).strftime(
                '%d/%m/%Y'
            )
            names.append(
                (eva.id, '{} in {} at {}'.format(prod_name, loc_name, date))
            )
        return names
