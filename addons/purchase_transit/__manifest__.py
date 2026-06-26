# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Transit Tracking',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Track in-transit shipping progress of purchase order lines (e.g. China -> Fiji)',
    'description': """
Purchase Transit Tracking
=========================
Per purchase-order-line shipping milestone visibility:
ordered -> factory shipped -> gate-in/loaded -> ETD/ATD -> transshipment
-> ETA/ATA -> customs cleared -> received in stock.

The "received in stock" milestone is auto-filled from the real incoming
stock move, so warehouse receipt closes the loop without re-keying.
""",
    'depends': ['purchase_stock', 'mail'],
    'data': [
        'security/purchase_transit_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/purchase_transit_views.xml',
        'views/purchase_order_views.xml',
        'views/res_config_settings_views.xml',
        'report/purchase_transit_analysis_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
