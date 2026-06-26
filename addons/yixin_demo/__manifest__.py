# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Yixin Demo Data',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Showcase data for 易新建筑: steel/ALC products with photos, '
               'stock balances, reorder alerts, purchase orders and '
               'China -> Fiji transit tracking at every milestone.',
    'depends': ['purchase_transit'],
    'data': [
        'data/product_category.xml',
        'data/res_partner.xml',
        'data/product_product.xml',
        'data/stock_orderpoint.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
