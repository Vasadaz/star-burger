import phonenumbers

from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.response import Response
from rest_framework.decorators import api_view

from .models import Order
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


@api_view(['POST'])
def register_order(request):
    order_notes = request.data

    def checking_order_field(field: str, field_type: type) -> dict:
        nonlocal order_notes

        if field not in order_notes:
            return {'error': f'{field} key not presented'}
        elif not isinstance(order_notes[field], field_type):
            return {'error': f'{field} key type is not {field_type}'}
        elif not order_notes[field]:
            return {'error': f'{field} key cannot be empty'}

    if products_field_errors := checking_order_field('products', list):
        return Response(products_field_errors)
    else:
        products_ids = Product.objects.values_list('id', flat=True)
        for product in order_notes['products']:
            product_id = product['product']
            if product_id not in products_ids:
                return Response({'error': f'product ID {product_id} not found'})

    if firstname_field_errors := checking_order_field('firstname', str):
        return Response(firstname_field_errors)

    if lastname_field_errors := checking_order_field('lastname', str):
        return Response(lastname_field_errors)

    if phonenumber_field_errors := checking_order_field('phonenumber', str):
        return Response(phonenumber_field_errors)
    else:
        order_phonenumber = phonenumbers.parse(order_notes['phonenumber'], 'RU')
        if not phonenumbers.is_valid_number(order_phonenumber):
            return Response({'error': f'phonenumber not valid'})

    if address_field_errors := checking_order_field('address', str):
        return Response(address_field_errors)

    order = Order(
        phonenumber=order_notes['phonenumber'],
        firstname=order_notes['firstname'],
        lastname=order_notes['lastname'],
        address=order_notes['address'],
    )
    order.save()

    for note in order_notes['products']:
        product = Product.objects.get(id=note['product'])
        order.products.add(
            product,
            through_defaults={'count': note['quantity']}
        )

    return Response({'status': 'CREATED', 'order': order_notes})
