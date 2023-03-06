from geopy import distance as calculate_distance
from django.db import models, utils
from django.core.validators import MinValueValidator
from django.utils.timezone import now
from phonenumber_field.modelfields import PhoneNumberField

from .geocoder import fetch_coordinates


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

    def get_coordinates(self) -> tuple[lon: float, lat: float]:
        if not self.lon or not self.lat:
            lon, lat = fetch_coordinates(self.address)
            self.lon = lon
            self.lat = lat
            self.save()

        return self.lon, self.lat


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
            price=models.Sum(models.F('kits__price'), output_field=models.DecimalField())
        ).order_by('status', 'id')


class Order(models.Model):
    STATUS_CHOICES = [
        ('1 not processed', 'Необработан'),
        ('2 cooking', 'Готовится'),
        ('3 on way', 'В пути'),
        ('4 delivered', 'Доставлен'),
    ]
    PAYMENT_CHOICES = [
        ('not specified', 'Не указана'),
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

    def get_verified_deliveries(self) -> list:
        order_products_ids = set(self.products.all().values_list('id', flat=True))
        verified_deliveries = []

        for delivery in self.deliveries.filter(order=self):
            restaurant_products_ids = set(
                delivery.restaurant.menu_items.filter(availability=True).values_list('product__id', flat=True)
            )

            if order_products_ids == (order_products_ids & restaurant_products_ids):
                verified_deliveries.append(delivery)

        return verified_deliveries

    def get_verified_restaurants(self) -> list[Restaurant]:
        verified_restaurants = []

        for delivery in self.get_verified_deliveries():
            verified_restaurants.append(delivery.restaurant)

        return verified_restaurants


class OrderKit(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='kits'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='продукт',
        related_name='kits'
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


class Delivery(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name='заказ',
        related_name='deliveries',
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        verbose_name='может приготовить ресторан',
        related_name='deliveries'
    )
    distance = models.PositiveIntegerField(
        verbose_name='расстояние доставки (м)',
        default=None,
        null=True,
    )

    class Meta:
        ordering = ['distance']
        verbose_name = 'ресторан приготовит продукт из заказа'
        verbose_name_plural = 'рестораны приготовят продукты из заказов'

    def __str__(self):
        if self.distance:
            return f'{self.restaurant} - {self.distance}м.'
        else:
            return f'{self.restaurant} - необходимо уточнить адрес!'

    def add_distance(self, max_distance=50000) -> None:
        client_coordinates = fetch_coordinates(self.order.address)
        restaurant_coordinates = self.restaurant.get_coordinates()

        if (distance := calculate_distance.distance(restaurant_coordinates, client_coordinates).m) < max_distance:
            self.distance = distance
        else:
            self.distance = None

        self.save(update_fields=['distance'])
