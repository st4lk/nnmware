from decimal import Decimal as D
from django.utils.timezone import now
from datetime import timedelta
from nnmware.tests.base import BaseTestCase
from model_mommy import mommy
from nnmware.apps.booking.models import PlacePrice
from django import forms


class PlacePriceForm(forms.ModelForm):
    class Meta:
        model = PlacePrice


class PriceTestCase(BaseTestCase):
    def setUp(self):
        self.today = now()
        one_day = timedelta(days=1)
        self.one_day = one_day
        self.next_day = self.today + one_day
        self.room = mommy.make('booking.Room')
        self.stl1 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=1)
        self.stl2 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=True, settlement=2)
        self.stl3 = mommy.make('booking.SettlementVariant',
            room=self.room, enabled=False, settlement=3)
        day_price = {
            self.today: [(self.stl1, 10), (self.stl2, 15), (self.stl3, 20)],
            self.next_day: [(self.stl1, 11), (self.stl2, 12), (self.stl3, 13)],
            self.next_day+one_day: [(self.stl1, 14), (self.stl2, 15), (self.stl3, 16)],
        }
        for date, prices in day_price.items():
            for stl, price in prices:
                mommy.make('booking.PlacePrice', date=date,
                    amount=price, settlement=stl)

    def test_price_days(self):
        td, nd, od = self.today, self.next_day, self.one_day
        prices = [
            # one day
            {'day_in': td, 'day_out': nd, "guests": 1, "total": D('10')},
            {'day_in': td, 'day_out': nd, "guests": 2, "total": D('15')},
            {'day_in': td, 'day_out': nd, "guests": 3, "total": None},
            # two days
            {'day_in': td, 'day_out': nd+od, "guests": 1, "total": D('21')},
            {'day_in': td, 'day_out': nd+od, "guests": 2, "total": D('27')},
            {'day_in': td, 'day_out': nd+od, "guests": 3, "total": None},
            # three days
            {'day_in': td, 'day_out': nd+od*2, "guests": 1, "total": D('35')},
            {'day_in': td, 'day_out': nd+od*2, "guests": 2, "total": D('42')},
            {'day_in': td, 'day_out': nd+od*2, "guests": 3, "total": None},
        ]
        for p in prices:
            price = self.room.get_price(date_in=p['day_in'],
                date_out=p['day_out'], guests=p['guests'])
            self.assertEqual(price, p['total'])

    def test_price_unique(self):
        pp = PlacePrice.objects.all()[0]
        f = PlacePriceForm(dict(amount=D('7'), date=pp.date,
                settlement=pp.settlement.pk))
        self.assertFalse(f.is_valid())
        self.assertIn(u'already exists', f.errors['__all__'][0])
