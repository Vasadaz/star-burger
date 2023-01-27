import requests

from geopy import distance
from django.db import transaction
from django.http import JsonResponse
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
from star_burger.settings import YANDEX_GEO_API


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


def fetch_coordinates(apikey: str, address: str):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

    return lat, lon


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
def register_order(request):
    order_serializer = OrderSerializer(data=request.data)
    order_serializer.is_valid(raise_exception=True)

    order = Order.objects.create(
        phonenumber=order_serializer.validated_data['phonenumber'],
        firstname=order_serializer.validated_data['firstname'],
        lastname=order_serializer.validated_data['lastname'],
        address=order_serializer.validated_data['address'],
    )

    client_coordinates = fetch_coordinates(YANDEX_GEO_API, order.address)

    order_restaurants = []
    for restaurant in Restaurant.objects.iterator():
        if not restaurant.lat or not restaurant.lon:
            lat, lon = fetch_coordinates(YANDEX_GEO_API, restaurant.address)
            restaurant.lat = lat
            restaurant.lon = lon
            restaurant.save()
        order_restaurants.append({
            'obj': restaurant,
            'distance_to_client': distance.distance((restaurant.lat, restaurant.lon), client_coordinates).m,
        })

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

    for order_restaurant in order_restaurants:
        order.restaurants.create(
            restaurant=order_restaurant['obj'],
            distance_to_client=order_restaurant['distance_to_client']
        )

    return Response(OrderSerializer(order).data)
