from rest_framework.serializers import IntegerField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ReadOnlyField

from .models import Order
from .models import OrderKit
from .models import Restaurant


class OrderKitSerializer(ModelSerializer):
    quantity = IntegerField(source='count')

    class Meta:
        model = OrderKit
        fields = ['product', 'quantity']


class OrderSerializer(ModelSerializer):
    price = ReadOnlyField()
    status = ReadOnlyField()
    payment = ReadOnlyField()
    comment = ReadOnlyField()
    products = OrderKitSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'firstname',
            'lastname',
            'address',
            'phonenumber',
            'products',
            'status',
            'payment',
            'comment',
            'price',
        ]

    def create(self) -> Order:
        order = Order.objects.create(
            phonenumber=self.validated_data['phonenumber'],
            firstname=self.validated_data['firstname'],
            lastname=self.validated_data['lastname'],
            address=self.validated_data['address'],
        )

        for product_notes in self.validated_data['products']:
            product = product_notes['product']
            count = product_notes['count']
            price = product.price * count
            order.products.add(
                product,
                through_defaults={
                    'count': count,
                    'price': price,
                }
            )

        for restaurant in Restaurant.objects.iterator():
            order.deliveries.create(
                restaurant=restaurant
            ).add_distance()

        return order
