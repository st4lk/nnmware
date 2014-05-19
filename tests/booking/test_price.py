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
    AUTO_CREATE_PRICE_DAYS = True

    def setUp(self):
        super(BasePriceTestCase, self).setUp()
        self.day1 = now()
        one_day = timedelta(days=1)
        for i in xrange(1, 10):
            setattr(self, 'day{0}'.format(i+1), self.day1 + one_day*i)
        self.hotel = mommy.make('booking.Hotel')
        self.room = mommy.make('booking.Room', hotel=self.hotel)
        self.stl1 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=1)
        self.stl2 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=2)
        self.stl3 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=False, settlement=3)
        self.cr = mommy.make('money.Currency', code='USD')
        if self.AUTO_CREATE_PRICE_DAYS:
            day_prices = self.get_day_price()
            self.create_day_prices(day_prices)

    def get_day_price(self):
        return {
            self.day1: [(self.stl1, 10), (self.stl2, 15), (self.stl3, 20)],
            self.day2: [(self.stl1, 11), (self.stl2, 12), (self.stl3, 13)],
            self.day3: [(self.stl1, 14), (self.stl2, 15), (self.stl3, 16)],
        }

    def create_day_prices(self, day_prices):
        for date, prices in day_prices.items():
            for stl, price in prices:
                mommy.make('booking.PlacePrice', date=date,
                    amount=price, settlement=stl, currency=self.cr)

    def create_discount(self, discount, mp):
        for date, value in (mp):
            mommy.make('booking.RoomDiscount', date=date,
                room=self.room, discount=discount, value=value)


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
            with self.assertNumQueries(1):
                guests_avaliable = self.room.settlement_for_guests(p['guests'])
                price = self.room.get_price(date_in=p['day_in'],
                    date_out=p['day_out'], guests=guests_avaliable)
                self.assertEqual(price, p['total'])

    def test_price_unique(self):
        pp = PlacePrice.objects.all()[0]
        f = PlacePriceForm(dict(amount=D('7'), date=pp.date,
                settlement=pp.settlement.pk))
        self.assertFalse(f.is_valid())
        self.assertIn(u'already exists', f.errors['__all__'][0])


class NormalDiscountTestCase(BasePriceTestCase):
    def setUp(self):
        super(NormalDiscountTestCase, self).setUp()
        self.disc_norm = mommy.make('booking.Discount', choice=DISCOUNT_NORMAL,
            hotel=self.hotel, apply_norefund=True, apply_creditcard=True)
        self.disc_norfd = mommy.make('booking.Discount', choice=DISCOUNT_NOREFUND,
            hotel=self.hotel, percentage=False)
        self.disc_card = mommy.make('booking.Discount', choice=DISCOUNT_CREDITCARD,
            hotel=self.hotel, percentage=True)
        mp = (self.day1, D('25')), (self.day2, D('15')), (self.day3, D('10'))
        self.create_discount(self.disc_norm, mp)

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
        self.create_discount(self.disc_norfd, mp)
        prices = self.room.get_price_discount(self.day1, self.day3, 2)
        self.assertEqual(prices, [D('21.45'), D('20.35'), D('21.45')])

    def test_normal_d2_g2_norefund_card(self):
        # NOREFUND discount
        mp = (self.day1, D('0.5')), (self.day2, D('0.6'))
        self.create_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('7'))
        self.create_discount(self.disc_card, mp)
        prices = self.room.get_price_discount(self.day1, self.day3, 2)
        self.assertEqual(prices, [D('21.45'), D('20.35'), D('20.1735')])

    def test_multi_group5(self):
        self.disc_norm.apply_norefund = False
        self.disc_norm.save()
        disc_spec = mommy.make('booking.Discount', choice=DISCOUNT_SPECIAL,
            hotel=self.hotel, apply_norefund=True, apply_creditcard=False)
        # SPECIAL discount
        mp = (self.day1, D('25')), (self.day2, D('15')), (self.day3, D('10'))
        self.create_discount(disc_spec, mp)
        # NOREFUND discount
        mp = (self.day1, D('0.5')), (self.day2, D('2'))
        self.create_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('7'))
        self.create_discount(self.disc_card, mp)

        prices = self.room.get_price_discount(self.day1, self.day3, 2)
        # (15*(1-0.25)) + (12*(1-0.15)) = 21.45 - discount special
        # (15*(1-0.25)) + (12*(1-0.15)) = 21.45 - discount norm

        # (15*(1-0.25)-0.5) + (12*(1-0.15)-2) = 18.95 - discount special & norefund
        # (15*(1-0.25)) + (12*(1-0.15)) = 21.45 - discount norm & norefund

        # (15*(1-0.25)) + (12*(1-0.15)) = 21.45 - discount special
        # (15*(1-0.25))*(1-0.05) + (12*(1-0.15))*(1-0.07) = 20.1735 - discount norm & card
        self.assertEqual(prices, [D('21.45'), D('18.95'), D('20.1735')])


class NormalPeriodDiscountTestCase(BasePriceTestCase):
    def setUp(self):
        super(NormalPeriodDiscountTestCase, self).setUp()
        self.disc_norm = mommy.make('booking.Discount', choice=DISCOUNT_NORMAL,
            hotel=self.hotel, apply_norefund=True, apply_creditcard=True,
            apply_period=True)
        self.disc_norfd = mommy.make('booking.Discount', choice=DISCOUNT_NOREFUND,
            hotel=self.hotel, percentage=True)
        self.disc_card = mommy.make('booking.Discount', choice=DISCOUNT_CREDITCARD,
            hotel=self.hotel, percentage=True)
        self.disc_period = mommy.make('booking.Discount', choice=DISCOUNT_PERIOD,
            hotel=self.hotel, percentage=False, apply_creditcard=True)

    def test_normal_period_norefund_card(self):
        # NORMAL DISCOUNT
        mp = (self.day1, D('12')), (self.day2, D('15')), (self.day3, D('10'))
        self.create_discount(self.disc_norm, mp)
        # PERIOD discount
        mp = (self.day1, D('3.5')), (self.day2, D('0.4')), (self.day3, D('0.6'))
        self.create_discount(self.disc_period, mp)
        # NOREFUND discount
        mp = (self.day1, D('3')), (self.day2, D('2'))
        self.create_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('4'))
        self.create_discount(self.disc_card, mp)

        prices = self.room.get_price_discount(self.day1, self.day3, 1)
        # 10*(1-0.12)-2.5 + 11*(1-0.15)-0.4 = 15.25 - norm & period
        # (10*(1-0.12)-2.5)*(1-0.03) + (11*(1-0.15)-0.4)*(1-0.02) = 14.882 - norm & period & norefund
        # (10*(1-0.12)-2.5)*(1-0.05) + (11*(1-0.15)-0.4)*(1-0.04) = 14.577 - norm & period & card
        self.assertEqual(prices, [D('15.25'), D('14.882'), D('14.577')])

    def test_normal_sep_period_norefund_card(self):
        # NORMAL DISCOUNT
        mp = (self.day1, D('12')), (self.day2, D('15')), (self.day3, D('10'))
        self.create_discount(self.disc_norm, mp)
        # PERIOD discount
        mp = (self.day1, D('3.5')), (self.day2, D('0.4')), (self.day3, D('0.6'))
        self.create_discount(self.disc_period, mp)
        # NOREFUND discount
        mp = (self.day1, D('3')), (self.day2, D('2'))
        self.create_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('4'))
        self.create_discount(self.disc_card, mp)

        self.disc_norm.apply_period = False
        self.disc_norm.save()
        self.disc_period.apply_norefund = False
        self.disc_norm.save()
        prices = self.room.get_price_discount(self.day1, self.day3, 1)
        # 10*(1-0.12) + 11*(1-0.15) = 18.15 - discount norm
        # 10*(1-0.12)*(1-0.03) + 11*(1-0.15)*(1-0.02) = 17.699 - norm & norefund
        # 10*(1-0.12)*(1-0.05) + 11*(1-0.15)*(1-0.04) = 17.336 - norm & card

        # 10-2.5 + 11-0.4 = 18.1 - period
        # 10-2.5 + 11-0.4 = 18.1 - period & norefund (not applicable)
        # (10-2.5)*(1-0.05) + (11-0.4)*(1-0.04) = 17.301 - period & card (not applicable)
        self.assertEqual(prices, [D('18.1'), D('17.699'), D('17.301')])

    def test_normal_period_no_norefund_no_card(self):
        # NORMAL DISCOUNT
        mp = (self.day1, D('12')), (self.day2, D('15')), (self.day3, D('10'))
        self.create_discount(self.disc_norm, mp)
        # PERIOD discount
        mp = (self.day1, D('3.5')), (self.day2, D('0.4')), (self.day3, D('0.6'))
        self.create_discount(self.disc_period, mp)
        # NOREFUND discount
        mp = (self.day1, D('30')), (self.day2, D('40'))
        self.create_discount(self.disc_norfd, mp)
        # CREDITCARD discount
        mp = (self.day1, D('5')), (self.day2, D('4'))
        self.create_discount(self.disc_card, mp)

        self.disc_period.apply_norefund = False
        self.disc_norm.save()
        prices = self.room.get_price_discount(self.day1, self.day3, 1)
        # 10*(1-0.12)-2.5 + 11*(1-0.15)-0.4 = 15.25 - norm & period
        # 10*(1-0.12)*(1-0.3) + 11*(1-0.15)*(1-0.4) = 11.77 - norm & norefund
        # (10*(1-0.12)-2.5)*(1-0.05) + (11*(1-0.15)-0.4)*(1-0.04) = 14.577 - norm & period & card

        self.assertEqual(prices, [D('15.25'), D('11.77'), D('14.577')])

    def test_normal_two_period(self):
        #TODO
        pass


class SinglePackageDiscountTestCase(BasePriceTestCase):
    AUTO_CREATE_PRICE_DAYS = False

    def setUp(self):
        super(SinglePackageDiscountTestCase, self).setUp()

    def create_pckg(self, disc_pckg, days=7):
        mp = []
        for d in range(1, days+1):
            mp.append((getattr(self, "day{0}".format(d))), 0)
        self.create_discount(disc_pckg, mp)

    def test_single_package_monotonic(self):
        # day price
        day_prices = {
            self.day1: [(self.stl2, 101), ],
            self.day2: [(self.stl2, 102), ],
            self.day3: [(self.stl2, 103), ],
            self.day4: [(self.stl2, 104), ],
            self.day5: [(self.stl2, 105), ],
            self.day6: [(self.stl2, 106), ],
            self.day7: [(self.stl2, 107), ],
        }
        self.create_day_prices(day_prices)
        # PACKAGE discount
        disc_pckg = mommy.make('booking.Discount', choice=DISCOUNT_PACKAGE,
            hotel=self.hotel, days=3, at_price_days=2)
        self.create_pckg(disc_pckg, days=7)

        prices = self.room.get_price_discount(self.day1, self.day8, 2)
        # (105+106)+(102+103)+101 = 517
        self.assertEqual(prices, [D('517'), D('517'), D('517')])

    def test_single_package_peak(self):
        # day price
        day_prices = {
            self.day1: [(self.stl2, 100), ],
            self.day2: [(self.stl2, 100), ],
            self.day3: [(self.stl2, 200), ],
            self.day4: [(self.stl2, 300), ],
            self.day5: [(self.stl2, 100), ],
            self.day6: [(self.stl2, 100), ],
            self.day7: [(self.stl2, 100), ],
        }
        self.create_day_prices(day_prices)
        # PACKAGE discount
        disc_pckg = mommy.make('booking.Discount', choice=DISCOUNT_PACKAGE,
            hotel=self.hotel, days=3, at_price_days=2)
        self.create_pckg(disc_pckg, days=7)

        prices = self.room.get_price_discount(self.day1, self.day8, 2)
        #  (100+200)+(100+100)+100 = 600
        self.assertEqual(prices, [D('600'), D('600'), D('600')])

    def test_single_package_very_peak(self):
        # day price
        day_prices = {
            self.day1: [(self.stl2, 100), ],
            self.day2: [(self.stl2, 100), ],
            self.day3: [(self.stl2, 100), ],
            self.day4: [(self.stl2, 100), ],
            self.day5: [(self.stl2, 1000), ],
            self.day6: [(self.stl2, 100), ],
            self.day7: [(self.stl2, 100), ],
        }
        self.create_day_prices(day_prices)
        # PACKAGE discount
        disc_pckg = mommy.make('booking.Discount', choice=DISCOUNT_PACKAGE,
            hotel=self.hotel, days=3, at_price_days=2)
        self.create_pckg(disc_pckg, days=7)

        prices = self.room.get_price_discount(self.day1, self.day8, 2)
        #  100+100+(100+100)+100+100 = 600
        self.assertEqual(prices, [D('600'), D('600'), D('600')])


class DoublePackageDiscountTestCase(BasePriceTestCase):
    #TODO
    pass
