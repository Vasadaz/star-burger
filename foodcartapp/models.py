import requests

from geopy import distance
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.timezone import now
from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )
    lat = models.DecimalField(
        verbose_name='широта',
        decimal_places=6,
        editable=False,
        max_digits=8,
        null=True,
    )
    lon = models.DecimalField(
        verbose_name='долгота',
        decimal_places=6,
        editable=False,
        max_digits=8,
        null=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=300,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f'{self.restaurant.name} - {self.product.name}'


class OrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().annotate(
            price=models.Sum(models.F('order_kits__price'), output_field=models.DecimalField())
        ).order_by('status', 'id')

    def check_status(self):
        self.filter(preparing_restaurant__isnull=False, status='1 not processed').update(status='2 cooking')


class Order(models.Model):
    STATUS_CHOICES = [
        ('1 not processed', 'Необработан'),
        ('2 cooking', 'Готовится'),
        ('3 on way', 'В пути'),
        ('4 delivered', 'Доставлен'),
    ]
    PAYMENT_CHOICES = [
        ('not specified', 'Не указан'),
        ('cash', 'Наличными'),
        ('card', 'Картой'),
        ('online', 'Онлайн'),
    ]

    phonenumber = PhoneNumberField(
        'телефон',
        db_index=True,
        region='RU',
    )
    status = models.CharField(
        verbose_name='статус',
        choices=STATUS_CHOICES,
        default='1 not processed',
        db_index=True,
        max_length=15,
    )
    payment = models.CharField(
        verbose_name='оплата',
        choices=PAYMENT_CHOICES,
        default='not specified',
        db_index=True,
        max_length=15,
    )
    firstname = models.CharField(
        'имя',
        max_length=50
    )
    lastname = models.CharField(
        'фамилия',
        max_length=50
    )
    address = models.CharField(
        'адрес доставки',
        max_length=150
    )
    registered_at = models.DateTimeField(
        verbose_name='оформлен',
        default=now,
        db_index=True,
        editable=True,
    )
    processed_at = models.DateTimeField(
        verbose_name='обработан',
        blank=True,
        null=True,
    )
    comment = models.TextField(
        verbose_name='комментарий',
        blank=True,
    )
    preparing_restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        verbose_name='Готовится в ресторане',
        blank=True,
        null=True,
    )
    delivered_at = models.DateTimeField(
        verbose_name='доставлен',
        blank=True,
        null=True,
    )
    products = models.ManyToManyField(
        Product,
        related_name='orders',
        through='OrderKit',
        through_fields=('order', 'product'),
        verbose_name='продукт',
    )

    objects = OrderManager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.phonenumber} {self.firstname} {self.lastname}'

    @staticmethod
    def fetch_coordinates(address: str):

        base_url = "https://geocode-maps.yandex.ru/1.x"
        response = requests.get(base_url, params=dict(geocode=address, apikey=settings.YANDEX_GEO_API, format="json"))
        response.raise_for_status()
        found_places = response.json()['response']['GeoObjectCollection']['featureMember']

        if not found_places:
            return None

        most_relevant = found_places[0]
        lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

        return lat, lon

    def _get_distance_to_restaurants(self) -> list[dict]:
        client_coordinates = self.fetch_coordinates(self.address)

        distances_to_restaurants = []
        for restaurant in Restaurant.objects.iterator():
            if not restaurant.lat or not restaurant.lon:
                lat, lon = self.fetch_coordinates(restaurant.address)
                restaurant.lat = lat
                restaurant.lon = lon
                restaurant.save()
            distances_to_restaurants.append({
                'restaurant': restaurant,
                'distance_to_client': distance.distance((restaurant.lat, restaurant.lon), client_coordinates).m,
            })

        return distances_to_restaurants

    @property
    def add_distances_to_restaurants(self) -> None:
        distance_to_restaurants = self._get_distance_to_restaurants()

        for distance_to_restaurant in distance_to_restaurants:
            self.distance_to_restaurants.create(
                restaurant=distance_to_restaurant['restaurant'],
                distance_to_client=distance_to_restaurant['distance_to_client']
            )

        return

    @property
    def update_distances_to_restaurants(self) -> None:
        self.distance_to_restaurants.all().delete()
        self.add_distances_to_restaurants

        return

    @property
    def get_verified_distances(self) -> list:
        order_products_ids = set(self.products.all().values_list('id', flat=True))
        verified_distances = []

        for distance in self.distance_to_restaurants.filter(order=self):
            restaurant_products_ids = set(
                distance.restaurant.menu_items.filter(availability=True).values_list('product__id', flat=True)
            )

            if order_products_ids == (order_products_ids & restaurant_products_ids):
                verified_distances.append(distance)

        return verified_distances

    @property
    def get_verified_restaurants(self) -> list:
        verified_restaurants = []

        for distance in self.get_verified_distances:
            verified_restaurants.append(distance.restaurant)

        return verified_restaurants


class OrderKit(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='order_kits'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='продукт',
        related_name='order_kits'
    )
    count = models.PositiveSmallIntegerField(
        verbose_name='количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        verbose_name='стоимость',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'состав заказа'
        verbose_name_plural = 'составы заказов'

    def __str__(self):
        return f'В заказе "{self.order}" есть "{self.product}" {self.count} шт.'


class Distance(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='distance_to_restaurants',
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        verbose_name='может приготовить ресторан',
        related_name='distance_to_clients'
    )
    distance_to_client = models.PositiveIntegerField(
        verbose_name='расстояние до клиента (м)',
    )

    class Meta:
        ordering = ['distance_to_client']
        verbose_name = 'ресторан приготовит продукт из заказа'
        verbose_name_plural = 'рестораны приготовят продукты из заказа'

    def __str__(self):
        return f'{self.restaurant} - {self.distance_to_client} м'
