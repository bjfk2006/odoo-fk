# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# (state_key, actual_date_field, planned_date_field_or_None)
# Ordered from first to last milestone. `state` is the latest milestone that
# has an actual date. See design doc §7.2.
MILESTONES = [
    ('ordered', 'date_ordered', None),
    ('factory_out', 'actual_factory_out', 'planned_factory_out'),
    ('gate_in', 'actual_gate_in', 'planned_gate_in'),
    ('departed', 'actual_atd', 'planned_etd'),
    ('transshipment', 'actual_transshipment', 'planned_transshipment'),
    ('arrived', 'actual_ata', 'planned_eta'),
    ('customs_cleared', 'actual_customs', 'planned_customs'),
    ('received', 'actual_received', 'planned_received'),
]
_ACTUAL_FIELDS = [m[1] for m in MILESTONES]
_PLANNED_FIELDS = [m[2] for m in MILESTONES if m[2]]


class PurchaseTransit(models.Model):
    _name = 'purchase.transit'
    _description = 'Purchase Transit Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_eta desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'))
    active = fields.Boolean(default=True)

    # --- Anchor: the purchase order line being tracked (design §7.1) ---
    purchase_line_id = fields.Many2one(
        'purchase.order.line', string='Purchase Order Line',
        required=True, ondelete='cascade', index=True, copy=False)
    order_id = fields.Many2one(
        'purchase.order', string='Purchase Order',
        related='purchase_line_id.order_id', store=True, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product',
        related='purchase_line_id.product_id', store=True)
    partner_id = fields.Many2one(
        'res.partner', string='Supplier',
        related='order_id.partner_id', store=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='order_id.company_id', store=True, index=True)
    product_qty = fields.Float(
        string='In-Transit Qty', related='purchase_line_id.product_qty',
        digits='Product Unit')
    qty_received = fields.Float(
        string='Received Qty', related='purchase_line_id.qty_received',
        digits='Product Unit')
    is_partial = fields.Boolean(
        string='Partially Received', compute='_compute_is_partial')

    # --- Shipping metadata (design §7.2) ---
    forwarder_id = fields.Many2one(
        'res.partner', string='Forwarder', tracking=True)
    transport_mode = fields.Selection(
        [('sea', 'Sea'), ('air', 'Air'), ('land', 'Land')],
        string='Transport Mode', default='sea', required=True, tracking=True)
    vessel_name = fields.Char(string='Vessel', tracking=True)
    voyage_no = fields.Char(string='Voyage No.', tracking=True)
    container_no = fields.Char(string='Container No.', tracking=True)
    bill_of_lading = fields.Char(string='B/L No.', tracking=True)
    incoterm_id = fields.Many2one(
        'account.incoterms', string='Incoterm',
        related='order_id.incoterm_id', store=True)
    pol = fields.Char(string='Port of Loading', help='Origin port (China).')
    pot = fields.Char(string='Transshipment Port')
    pod = fields.Selection(
        [('suva', 'Suva (FJSUV)'),
         ('lautoka', 'Lautoka (FJLTK)'),
         ('other', 'Other')],
        string='Port of Discharge', default='suva',
        help='Destination port in Fiji.')

    # --- Milestones: planned + actual (design §7.2), day granularity ---
    date_ordered = fields.Date(
        string='Ordered', compute='_compute_date_ordered', store=True,
        help='Order confirmation date (date part of the PO approval datetime).')
    planned_factory_out = fields.Date(string='Planned Factory Out')
    actual_factory_out = fields.Date(string='Actual Factory Out', tracking=True)
    planned_gate_in = fields.Date(string='Planned Gate-in')
    actual_gate_in = fields.Date(string='Actual Gate-in', tracking=True)
    planned_etd = fields.Date(string='ETD')
    actual_atd = fields.Date(string='ATD (Departed)', tracking=True)
    planned_transshipment = fields.Date(string='Planned Transshipment')
    actual_transshipment = fields.Date(string='Actual Transshipment', tracking=True)
    planned_eta = fields.Date(string='ETA')
    actual_ata = fields.Date(string='ATA (Arrived)', tracking=True)
    planned_customs = fields.Date(string='Planned Customs')
    actual_customs = fields.Date(string='Actual Customs Cleared', tracking=True)
    planned_received = fields.Date(string='Planned Received')
    actual_received = fields.Date(
        string='Actual Received', tracking=True, copy=False,
        help='Auto-filled when the related incoming stock move is done; '
             'may be adjusted manually.')

    # --- State & metrics (design §7.2) ---
    state = fields.Selection(
        [(m[0], m[0].replace('_', ' ').title()) for m in MILESTONES],
        string='Status', compute='_compute_state', store=True,
        tracking=True, readonly=True,
        help='Latest reached milestone (derived from the actual dates).')
    is_late = fields.Boolean(
        string='Late', compute='_compute_is_late', store=True,
        help='The next pending milestone is past its planned date.')
    eta_delay_days = fields.Integer(
        string='ETA Delay (days)', compute='_compute_eta_delay_days', store=True)
    transit_days = fields.Integer(
        string='Transit Days', compute='_compute_transit_days', store=True,
        help='Days between departure (ATD) and receipt.')
    note = fields.Html(string='Notes')

    _sql_constraints = [
        ('purchase_line_uniq', 'unique(purchase_line_id)',
         'A transit record already exists for this purchase order line.'),
    ]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('order_id.date_approve')
    def _compute_date_ordered(self):
        for rec in self:
            rec.date_ordered = fields.Date.to_date(rec.order_id.date_approve) \
                if rec.order_id.date_approve else False

    @api.depends('product_qty', 'qty_received')
    def _compute_is_partial(self):
        for rec in self:
            rec.is_partial = 0 < rec.qty_received < rec.product_qty

    @api.depends(*_ACTUAL_FIELDS)
    def _compute_state(self):
        for rec in self:
            current = 'ordered'
            for state_key, actual_field, _planned in MILESTONES:
                if rec[actual_field]:
                    current = state_key
            rec.state = current

    @api.depends(*_ACTUAL_FIELDS, *_PLANNED_FIELDS)
    def _compute_is_late(self):
        today = fields.Date.context_today(self)
        for rec in self:
            late = False
            if rec.state != 'received':
                for _state_key, actual_field, planned_field in MILESTONES:
                    if not planned_field:
                        continue
                    if not rec[actual_field]:
                        # First pending milestone with a plan defines lateness.
                        if rec[planned_field] and rec[planned_field] < today:
                            late = True
                        break
            rec.is_late = late

    @api.depends('actual_ata', 'planned_eta')
    def _compute_eta_delay_days(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.actual_ata and rec.planned_eta:
                rec.eta_delay_days = (rec.actual_ata - rec.planned_eta).days
            elif rec.planned_eta and not rec.actual_ata and rec.planned_eta < today:
                rec.eta_delay_days = (today - rec.planned_eta).days
            else:
                rec.eta_delay_days = 0

    @api.depends('actual_received', 'actual_atd')
    def _compute_transit_days(self):
        for rec in self:
            if rec.actual_received and rec.actual_atd:
                rec.transit_days = (rec.actual_received - rec.actual_atd).days
            else:
                rec.transit_days = 0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains(*_ACTUAL_FIELDS)
    def _check_milestone_order(self):
        """Actual dates, where set, must be chronologically non-decreasing."""
        for rec in self:
            previous_key = None
            previous_date = None
            for state_key, actual_field, _planned in MILESTONES:
                value = rec[actual_field]
                if not value:
                    continue
                if previous_date and value < previous_date:
                    raise ValidationError(_(
                        "Milestone dates are out of order: '%(later)s' (%(later_date)s) "
                        "is earlier than '%(earlier)s' (%(earlier_date)s).",
                        later=state_key, later_date=value,
                        earlier=previous_key, earlier_date=previous_date))
                previous_key, previous_date = state_key, value

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'purchase.transit') or _('New')
        return super().create(vals_list)

    def action_view_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Cron (design §5.2, opt-in enabled per §11 Q4)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_delays(self):
        """Create a follow-up activity on late, not-yet-received records."""
        late_records = self.search([
            ('is_late', '=', True),
            ('state', '!=', 'received'),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for rec in late_records:
            # Idempotent: skip if an open activity already exists.
            if rec.activity_ids.filtered(lambda a: a.activity_type_id == activity_type):
                continue
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Shipment delayed: %s', rec.name),
                note=_('The next milestone is past its planned date. Please follow up.'),
                user_id=rec.create_uid.id or self.env.uid)
