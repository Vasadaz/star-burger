from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html

from .models import Order
from .models import Product
from .models import ProductCategory
from .models import Restaurant
from .models import RestaurantMenuItem


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [
        RestaurantMenuItemInline
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [
        RestaurantMenuItemInline
    ]
    fieldsets = (
        ('Общее', {
            'fields': [
                'name',
                'category',
                'image',
                'get_image_preview',
                'price',
            ]
        }),
        ('Подробно', {
            'fields': [
                'special_status',
                'description',
            ],
            'classes': [
                'wide'
            ],
        }),
    )

    readonly_fields = [
        'get_image_preview',
    ]

    class Media:
        css = {
            "all": (
                static("admin/foodcartapp.css")
            )
        }

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)

    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>', edit_url=edit_url,
                           src=obj.image.url)

    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass


class ProductInline(admin.TabularInline):
    can_delete = False
    model = Product.orders.through
    extra = 0
    readonly_fields = [
        'price',
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    def get_form(self, request, obj=None, **kwargs):
        form = super(OrderAdmin, self).get_form(request, obj, **kwargs)

        form.base_fields['preparing_restaurant'].queryset = Restaurant.objects.filter(
            distance_to_clients__order=obj,
            name__in=obj.get_verified_restaurants
        ).order_by('distance_to_clients__distance_to_client')

        return form

    def save_formset(self, request, form, formset, change):
        if 'address' in form.changed_data:
            form.instance.update_distances_to_restaurants

        try:
            product = Product.objects.get(id=request.POST['order_kits-0-product'])
            count = int(request.POST['order_kits-0-count'])
        except KeyError:
            product = Product.objects.get(id=request.POST['order_kits-0-product'])
            count = int(request.POST['order_kits-0-count'])

        instances = formset.save(commit=False)

        for instance in instances:
            instance.price = product.price * count
            instance.save()

        formset.save_m2m()

    def response_post_save_change(self, request, obj):
        response = super().response_post_save_change(request, obj)
        if "next" in request.GET:
            return HttpResponseRedirect(request.GET['next'])
        else:
            return response

    inlines = [ProductInline]
    list_display = [
        'phonenumber',
        'firstname',
        'address',
    ]
