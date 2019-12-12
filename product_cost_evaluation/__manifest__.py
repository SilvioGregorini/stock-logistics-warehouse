# Copyright (C) 2019 Sergio Corato
# Copyright (C) 2019 Silvio Gregorini (silviogregorini@openforce.it)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': "Product cost evaluation",
    'version': '11.0.1.0.0',
    'depends': [
        # 'stock_inventory_date',  # todo module to backdating inventory
        'purchase',
        'stock',
    ],
    'author': "Sergio Corato, Alex Comba, Silvio Gregorini,"
              " Odoo Community Association (OCA)",
    'website': 'https://github.com/OCA/stock-logistics-warehouse',
    'category': 'Warehouse Management',
    'installable': True,
    'license': 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/product_cost_evaluation_history.xml',
        'views/stock_inventory.xml',
    ]
}
