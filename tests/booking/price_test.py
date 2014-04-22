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
        self.cr = mommy.make('money.Currency', code='USD')
        for date, prices in day_price.items():
            for stl, price in prices:
                mommy.make('booking.PlacePrice', date=date,
                    amount=price, settlement=stl, currency=self.cr)


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


class DiscountTestCase(BasePriceTestCase):
    def setUp(self):
        super(DiscountTestCase, self).setUp()
        self.disc_norm = mommy.make('booking.Discount', choice=DISCOUNT_NORMAL,
            hotel=self.hotel, apply_norefund=True, apply_creditcard=True)
        self.disc_norfd = mommy.make('booking.Discount', choice=DISCOUNT_NOREFUND,
            hotel=self.hotel, percentage=False)
        self.disc_card = mommy.make('booking.Discount', choice=DISCOUNT_CREDITCARD,
            hotel=self.hotel, percentage=True)
        discounts = {
            self.day1: [
                dict(discount=self.disc_norm, value=25),
            ],
            self.day2: [
                dict(discount=self.disc_norm, value=15),
            ],
            self.day3: [
                dict(discount=self.disc_norm, value=10),
            ],
        }
        for date, d_list in discounts.items():
            for d_kwargs in d_list:
                mommy.make('booking.RoomDiscount', date=date,
                    room=self.room, **d_kwargs)

    def create_additional_discount(self, discount, mp):
        for date, value in (mp):
            mommy.make('booking.RoomDiscount', date=date,
                room=self.room, discount=discount, value=value)

    def test_normal_d1_g1(self):
        prices = self.room.get_price_discount(self.day1, self.day2, 1)
        self.assertEqual(prices, [D('7.5'), D('7.5'), D('7.5')])

    def test_normal_d2_g1(self):
        prices = self.room.get_price_discount(self.day1, self.day3, 1)
        self.assertEqual(prices, [D('16.85'), D('16.85'), D('16.85')])

    def test_normal_d3_g1(self):
        prices = self.room.get_price_discount(self.day1, self.day4, 1)
        self.assertEqual(prices, [D('29.45'), D('29.45'), D('29.45')])

    def test_normal_d3_g2(self):
        prices = self.room.get_price_discount(self.day1, self.day4, 2)
        self.assertEqual(prices, [D('34.95'), D('34.95'), D('34.95')])

    def test_normal_d3_g3(self):
        prices = self.room.get_price_discount(self.day1, self.day4, 3)
        self.assertEqual(prices, None)

    def test_normal_d2_g2_norefund(self):
        mp = (self.day1, D('0.5')), (self.day2, D('0.6'))
        self.create_additional_discount(self.disc_norfd, mp)
        prices = self.room.get_price_discount(self.day1, self.day3, 2)
        self.assertEqual(prices, [D('21.45'), D('20.35'), D('21.45')])

    def test_normal_d2_g2_norefund_card(self):
        # NOREFUND discount
        mp = (self.day1, D('0.5')), (self.day2, D('0.6'))
        self.create_additional_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('7'))
        self.create_additional_discount(self.disc_card, mp)
        prices = self.room.get_price_discount(self.day1, self.day3, 2)
        self.assertEqual(prices, [D('21.45'), D('20.35'), D('20.1735')])
