# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django_fsm import transition
from shop.models.order import OrderModel
from .base import PaymentProvider


class ForwardFundPayment(PaymentProvider):
    """
    Provides a simple prepayment payment provider.
    """
    namespace = 'forward-fund-payment'

    def get_payment_request(self, cart, request):
        order = OrderModel.objects.create_from_cart(cart, request)
        if order.total == 0:
            order.no_payment_required()
        else:
            order.awaiting_payment()
        order.save()
        thank_you_url = OrderModel.objects.get_latest_url()
        return '$window.location.href="{}";'.format(thank_you_url)


class PayInAdvanceWorkflowMixin(object):
    """
    Add this class to `settings.SHOP_ORDER_WORKFLOWS` to mix it into your `OrderModel`.
    It adds all the methods required for state transitions, when used with the
    `ForwardFundPayment` provider from above.
    """
    TRANSITION_TARGETS = {
        'awaiting_payment': _("Awaiting a forward fund payment"),
        'prepayment_deposited': _("Prepayment deposited"),
        'no_payment_required': _("No Payment Required"),
    }

    def is_fully_paid(self):
        return super(PayInAdvanceWorkflowMixin, self).is_fully_paid()

    @transition(field='status', source=['created'], target='no_payment_required')
    def no_payment_required(self):
        """
        Signals that an Order can proceed directly and by confirming a payment of value zero.
        """

    @transition(field='status', source=['created'], target='awaiting_payment')
    def awaiting_payment(self):
        """
        Signals that an Order awaits payments.
        Invoked by ForwardFundPayment.get_payment_request.
        """

    def deposited_too_little(self):
        return self.amount_paid > 0 and self.amount_paid < self.total

    @transition(field='status', source=['awaiting_payment'], target='awaiting_payment',
        conditions=[deposited_too_little], custom=dict(admin=True, button_name=_("Deposited too little")))
    def prepayment_partially_deposited(self):
        """Signals that an Order received a payment, which was not enough."""

    @transition(field='status', source=['awaiting_payment'], target='prepayment_deposited',
        conditions=[is_fully_paid], custom=dict(admin=True, button_name=_("Mark as Paid")))
    def prepayment_fully_deposited(self):
        """Signals that an Order received a payment, which fully covers the requested sum."""

    @transition(field='status', source=['prepayment_deposited', 'no_payment_required'],
        custom=dict(auto=True))
    def acknowledge_prepayment(self):
        """Ackknowledge the payment. This method is invoked automatically."""
        self.acknowledge_payment()


class CommissionGoodsWorkflowMixin(object):
    """
    Add this class to `settings.SHOP_ORDER_WORKFLOWS` to mix it into your `OrderModel`.
    It adds all the methods required for state transitions, while picking and packing the
    ordered goods for delivery.
    """
    TRANSITION_TARGETS = {
        'pick_goods': _("Picking goods"),
        'pack_goods': _("Packing goods"),
    }

    @transition(field='status', source=['payment_confirmed'], target='pick_goods',
        custom=dict(admin=True, button_name=_("Pick the goods")))
    def pick_goods(self, by=None):
        """Change status to 'pick_goods'."""

    @transition(field='status', source=['pick_goods'],
        target='pack_goods', custom=dict(admin=True, button_name=_("Pack the goods")))
    def pack_goods(self, by=None):
        """Change status to 'pack_goods'."""
