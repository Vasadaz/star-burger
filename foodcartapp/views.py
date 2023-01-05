from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import IntegerField
from rest_framework.serializers import ReadOnlyField
from rest_framework.serializers import CharField

from .models import Order
from .models import OrderKit
from .models import Product


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
            'price',
        ]


@api_view(['POST'])
def register_order(request):
    order_serializer = OrderSerializer(data=request.data)
    order_serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        phonenumber=order_serializer.validated_data['phonenumber'],
        firstname=order_serializer.validated_data['firstname'],
        lastname=order_serializer.validated_data['lastname'],
        address=order_serializer.validated_data['address'],
    )

    for product in order_serializer.validated_data['products']:
        order.products.add(
            product['product'],
            through_defaults={'count': product['count']}
        )

    return Response(OrderSerializer(order).data)
