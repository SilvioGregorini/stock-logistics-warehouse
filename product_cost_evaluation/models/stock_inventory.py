# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    evaluation_count = fields.Integer(
        compute='compute_evaluation_count',
        store=True,
        string="Purchase Evaluations Num"
    )

    evaluation_ids = fields.One2many(
        'product.cost.evaluation.history',
        'inventory_id',
        store=True,
        string="Purchase Evaluations"
    )

    @api.multi
    @api.depends('evaluation_ids')
    def compute_evaluation_count(self):
        for inventory in self:
            inventory.evaluation_count = len(inventory.evaluation_ids)

    @api.multi
    def action_view_evaluations(self):
        act = self.env.ref(
            'product_cost_evaluation.action_product_cost_evaluation_history'
        )
        action = act.read(load='')[0]
        action['domain'] = [('id', 'in', self.evaluation_ids.ids)]
        return action

    @api.multi
    def set_evaluations(self):
        if self.evaluation_ids:
            self.evaluation_ids.unlink()
        for line in self.mapped('line_ids'):
            line.set_evaluation()
        if self._context.get('show_evaluations'):
            return self.action_view_evaluations()
