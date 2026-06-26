# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command

# code -> on-hand quantity
ONHAND = {
    "GC-GJ-RB20": 8000, "GC-GJ-RB25": 6000, "GC-GJ-HB200": 12000, "GC-GJ-IB20": 5000,
    "GC-GJ-AG63": 3000, "GC-GJ-CH16": 2500, "GC-GJ-PP108": 4000, "GC-GJ-SH25": 9000,
    "GC-ALC-P100": 1200, "GC-ALC-B100": 8000, "GC-INS-01": 600,
    "HC-WELD-322": 5, "HC-CUT-400": 400, "HC-PPE-HAT": 150,
    "BJ-TOOL-AG": 12, "BJ-BRG-6206": 80, "OF-A4-70": 60, "OF-PEN-05": 200,
}

_COMMON = {"pol": "天津港", "pod": "suva"}


def _p(env, code):
    return env.ref("yixin_demo.product_" + code.replace("-", "_"))


def _receive(po):
    for pick in po.picking_ids:
        for m in pick.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        pick.button_validate()


def _tr(env, po, code):
    return env["purchase.transit"].search(
        [("order_id", "=", po.id), ("product_id", "=", _p(env, code).id)])


def post_init_hook(env):
    """Build the Yixin showcase: stock balances, purchase orders, receipts and
    China -> Fiji transit tracking at different milestones. The declarative
    master data (categories, suppliers, products, reorder rules) is loaded from
    data/*.xml; this hook does the transactional parts XML cannot express."""
    env.company.write({"name": "唐山市易新建筑科技有限责任公司"})
    forwarder = env.ref("yixin_demo.partner_ff")
    common = dict(_COMMON, forwarder_id=forwarder.id)

    # 1) On-hand inventory
    Quant = env["stock.quant"].with_context(inventory_mode=True)
    loc = env.ref("stock.stock_location_stock")
    for code, qty in ONHAND.items():
        q = Quant.create({"product_id": _p(env, code).id,
                          "location_id": loc.id, "inventory_quantity": qty})
        q.action_apply_inventory()

    # 2) Domestic PO -> received into stock
    PO = env["purchase.order"]
    tg = env.ref("yixin_demo.partner_tg")
    sg = env.ref("yixin_demo.partner_sg")
    po1 = PO.create({"partner_id": tg.id, "origin": "DEMO-IN-1", "order_line": [
        Command.create({"product_id": _p(env, "GC-GJ-RB20").id, "product_qty": 2000, "price_unit": 3.9}),
        Command.create({"product_id": _p(env, "GC-GJ-HB200").id, "product_qty": 3000, "price_unit": 4.6}),
    ]})
    po1.button_confirm()
    _receive(po1)

    # 3) Import PO -> 3 lines, transit at departed / arrived / customs_cleared
    po2 = PO.create({"partner_id": tg.id, "origin": "DEMO-IMP-1", "order_line": [
        Command.create({"product_id": _p(env, "GC-GJ-HB200").id, "product_qty": 5000, "price_unit": 4.5}),
        Command.create({"product_id": _p(env, "GC-GJ-RB25").id, "product_qty": 4000, "price_unit": 3.78}),
        Command.create({"product_id": _p(env, "GC-GJ-IB20").id, "product_qty": 3000, "price_unit": 4.32}),
    ]})
    po2.button_confirm()
    po2.action_generate_transit()
    _tr(env, po2, "GC-GJ-HB200").write(dict(common, vessel_name="中远海运室女座", voyage_no="CSCL-2607E",
        container_no="CCLU7788990", planned_factory_out="2026-06-01", actual_factory_out="2026-06-02",
        planned_gate_in="2026-06-05", actual_gate_in="2026-06-06", planned_etd="2026-06-08",
        actual_atd="2026-06-09", planned_eta="2026-07-18"))
    _tr(env, po2, "GC-GJ-RB25").write(dict(common, vessel_name="中远海运室女座", voyage_no="CSCL-2606W",
        container_no="CCLU7788991", planned_factory_out="2026-05-20", actual_factory_out="2026-05-21",
        planned_gate_in="2026-05-24", actual_gate_in="2026-05-25", planned_etd="2026-05-28",
        actual_atd="2026-05-29", planned_eta="2026-06-22", actual_ata="2026-06-24"))
    _tr(env, po2, "GC-GJ-IB20").write(dict(common, vessel_name="中远海运室女座", voyage_no="CSCL-2605W",
        container_no="CCLU7788992", planned_factory_out="2026-05-10", actual_factory_out="2026-05-11",
        planned_gate_in="2026-05-14", actual_gate_in="2026-05-15", planned_etd="2026-05-18",
        actual_atd="2026-05-19", planned_eta="2026-06-15", actual_ata="2026-06-16",
        planned_customs="2026-06-20", actual_customs="2026-06-22"))

    # 4) Import PO -> received (transit auto-closes via stock move)
    po3 = PO.create({"partner_id": sg.id, "origin": "DEMO-IMP-2", "order_line": [
        Command.create({"product_id": _p(env, "GC-GJ-PP108").id, "product_qty": 2000, "price_unit": 5.5}),
    ]})
    po3.button_confirm()
    po3.action_generate_transit()
    _tr(env, po3, "GC-GJ-PP108").write(dict(common, vessel_name="中远海运金牛座", voyage_no="CSCL-2604W",
        container_no="CCLU7788980", planned_factory_out="2026-04-20", actual_factory_out="2026-04-21",
        planned_gate_in="2026-04-24", actual_gate_in="2026-04-25", planned_etd="2026-04-28",
        actual_atd="2026-04-29", planned_eta="2026-05-25", actual_ata="2026-05-26",
        planned_customs="2026-05-29", actual_customs="2026-05-30"))
    _receive(po3)
