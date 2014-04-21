from nnmware.tests.base import BaseTestCase
from model_mommy import mommy


class PriceTestCase(BaseTestCase):
    def test_one_date_price(self):
        hotel = mommy.make('booking.Hotel')
        self.assertEqual(hotel.current_amount, 0)
