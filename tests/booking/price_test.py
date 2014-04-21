from decimal import Decimal as D
from datetime import timedelta
from django.utils.timezone import now
from django import forms
from model_mommy import mommy

from nnmware.apps.booking.models import (PlacePrice, DISCOUNT_UNKNOWN,
    DISCOUNT_NOREFUND, DISCOUNT_EARLY, DISCOUNT_LATER, DISCOUNT_PERIOD,
    DISCOUNT_PACKAGE, DISCOUNT_HOLIDAY, DISCOUNT_SPECIAL, DISCOUNT_LAST_MINUTE,
    DISCOUNT_CREDITCARD, DISCOUNT_NORMAL)
from nnmware.tests.base import BaseTestCase


class PlacePriceForm(forms.ModelForm):
    class Meta:
        model = PlacePrice


class BasePriceTestCase(BaseTestCase):
    def setUp(self):
        super(BasePriceTestCase, self).setUp()
        self.day1 = now()
        one_day = timedelta(days=1)
        for i in xrange(1, 7):
            setattr(self, 'day{0}'.format(i+1), self.day1 + one_day*i)
        self.hotel = mommy.make('booking.Hotel')
        self.room = mommy.make('booking.Room', hotel=self.hotel)
        self.stl1 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=1)
        self.stl2 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=2)
        self.stl3 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=False, settlement=3)
        day_price = {
            self.day1: [(self.stl1, 10), (self.stl2, 15), (self.stl3, 20)],
            self.day2: [(self.stl1, 11), (self.stl2, 12), (self.stl3, 13)],
            self.day3: [(self.stl1, 14), (self.stl2, 15), (self.stl3, 16)],
        }
        for date, prices in day_price.items():
            for stl, price in prices:
                mommy.make('booking.PlacePrice', date=date,
                    amount=price, settlement=stl)


class PriceTestCase(BasePriceTestCase):

    def test_price_days(self):
        d1, d2, d3, d4 = self.day1, self.day2, self.day3, self.day4
        prices = [
            # one day
            {'day_in': d1, 'day_out': d2, "guests": 1, "total": D('10')},
            {'day_in': d1, 'day_out': d2, "guests": 2, "total": D('15')},
            {'day_in': d1, 'day_out': d2, "guests": 3, "total": None},
            # two days
            {'day_in': d1, 'day_out': d3, "guests": 1, "total": D('21')},
            {'day_in': d1, 'day_out': d3, "guests": 2, "total": D('27')},
            {'day_in': d1, 'day_out': d3, "guests": 3, "total": None},
            # three days
            {'day_in': d1, 'day_out': d4, "guests": 1, "total": D('35')},
            {'day_in': d1, 'day_out': d4, "guests": 2, "total": D('42')},
            {'day_in': d1, 'day_out': d4, "guests": 3, "total": None},
        ]
        for cnt, p in enumerate(prices):
            price = self.room.get_price(date_in=p['day_in'],
                date_out=p['day_out'], guests=p['guests'])
            self.assertEqual(price, p['total'])

    def test_price_unique(self):
        pp = PlacePrice.objects.all()[0]
        f = PlacePriceForm(dict(amount=D('7'), date=pp.date,
                settlement=pp.settlement.pk))
        self.assertFalse(f.is_valid())
        self.assertIn(u'already exists', f.errors['__all__'][0])
