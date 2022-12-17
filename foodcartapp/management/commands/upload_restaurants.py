import json

from django.core.management.base import BaseCommand

from foodcartapp.models import Restaurant


class Command(BaseCommand):
    help = 'Start adding restaurants'

    def handle(self, *args, **options):

        with open(options['path'], 'r', encoding='utf-8') as file:
            restaurants = json.load(file)

        for restaurant in restaurants:
            self.add_restaurant(restaurant)

    def add_arguments(self, parser):
        parser.add_argument(
            'path',
            nargs='?',
            type=str,
        )

    def add_restaurant(self, restaurant_notes: dict):
        restaurant, created = Restaurant.objects.get_or_create(
            name=restaurant_notes['title'],
            defaults={
                'address': restaurant_notes.get('address', ''),
                'contact_phone': restaurant_notes.get('contact_phone', ''),
            }
        )

        if created:
            self.stdout.write(f'Added restaurant "{restaurant}".')
        else:
            self.stdout.write(f'\033[93mDOUBLE:\033[0m restaurant "{restaurant}" already exists!')
