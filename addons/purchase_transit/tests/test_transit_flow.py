# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTransitFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env['res.partner'].create({'name': 'CN Supplier'})
        cls.product = cls.env['product.product'].create({
            'name': 'Imported Widget',
            'is_storable': True,
        })
        cls.Transit = cls.env['purchase.transit']

    def _new_confirmed_po(self, qty=10.0):
        po = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'product_qty': qty,
                'price_unit': 100.0,
            })],
        })
        po.button_confirm()
        return po

    def _receive_all(self, po):
        picking = po.picking_ids[0]
        picking.move_ids.quantity = po.order_line.product_qty
        picking.move_ids.picked = True
        picking.button_validate()
        return picking

    def test_generate_and_receive_closes_loop(self):
        """Core闭环: 生成在途 -> 收货 done -> actual_received 自动回填。"""
        po = self._new_confirmed_po()
        po.action_generate_transit()
        transit = self.Transit.search([('order_id', '=', po.id)])
        self.assertEqual(len(transit), 1)
        self.assertEqual(transit.state, 'ordered')
        self.assertFalse(transit.actual_received)
        self.assertTrue(transit.name.startswith('TR/'))

        self._receive_all(po)

        self.assertTrue(
            transit.actual_received,
            "received milestone should be auto-filled from the stock move")
        self.assertEqual(transit.state, 'received')

    def test_generate_is_idempotent(self):
        """重复生成不应建出重复在途记录。"""
        po = self._new_confirmed_po()
        po.action_generate_transit()
        po.action_generate_transit()
        self.assertEqual(
            self.Transit.search_count([('order_id', '=', po.id)]), 1)

    def test_milestone_date_order_constraint(self):
        """实际日期逆序应触发 ValidationError。"""
        po = self._new_confirmed_po()
        po.action_generate_transit()
        transit = self.Transit.search([('order_id', '=', po.id)])
        with self.assertRaises(ValidationError):
            transit.write({
                'actual_atd': '2026-02-10',
                'actual_ata': '2026-02-01',  # earlier than ATD
            })

    def test_receipt_not_blocked_without_transit(self):
        """没有在途记录时收货必须照常完成（韧性: 跟踪失败不挡收货）。"""
        po = self._new_confirmed_po()
        # deliberately do NOT generate any transit record
        self._receive_all(po)
        self.assertEqual(
            po.order_line.qty_received, po.order_line.product_qty)

    def test_state_progression_and_eta_delay(self):
        """状态随实际日期推进；ETA 延误天数正确。"""
        po = self._new_confirmed_po()
        po.action_generate_transit()
        transit = self.Transit.search([('order_id', '=', po.id)])

        transit.actual_factory_out = '2026-02-01'
        self.assertEqual(transit.state, 'factory_out')
        transit.actual_atd = '2026-02-05'
        self.assertEqual(transit.state, 'departed')
        transit.planned_eta = '2026-02-18'
        transit.actual_ata = '2026-02-20'
        self.assertEqual(transit.state, 'arrived')
        self.assertEqual(transit.eta_delay_days, 2)
        self.assertEqual(transit.transit_days, 15)

    def test_partial_receipt_flag(self):
        """部分收货: is_partial=True 且仍标记 received。"""
        po = self._new_confirmed_po(qty=10.0)
        po.action_generate_transit()
        transit = self.Transit.search([('order_id', '=', po.id)])

        picking = po.picking_ids[0]
        picking.move_ids.quantity = 4.0
        picking.move_ids.picked = True
        # Receiving 4 of 10 pops a "Create Backorder?" wizard; confirm it.
        action = picking.button_validate()
        Form.from_action(self.env, action).save().process()

        self.assertEqual(transit.state, 'received')
        self.assertTrue(transit.is_partial)
