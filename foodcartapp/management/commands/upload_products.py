import json

from pathlib import Path

from django.core.management.base import BaseCommand

def main():
    print('OK')


class Command(BaseCommand):
    help = 'Start adding dishes'

    def handle(self, *args, **options):
        main()
