from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.serializers import IntegerField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import ReadOnlyField

from .models import Order
from .models import OrderKit
from .models import Product
from .models import Restaurant


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


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


@transaction.atomic(durable=True)
@api_view(['POST'])
def register_order(request) -> Response | HttpResponseBadRequest:
    order_serializer = OrderSerializer(data=request.data)
    order_serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        phonenumber=order_serializer.validated_data['phonenumber'],
        firstname=order_serializer.validated_data['firstname'],
        lastname=order_serializer.validated_data['lastname'],
        address=order_serializer.validated_data['address'],
    )

    for product_notes in order_serializer.validated_data['products']:
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
    try:
        for restaurant in Restaurant.objects.iterator():
            order.distance_to_restaurants.create(
                restaurant=restaurant
            ).add_distance()

    except ValueError:
        order.delete()
        return HttpResponseBadRequest('Адрес указан не корректно. Мы не можем найти его координаты.')

    return Response(OrderSerializer(order).data)
