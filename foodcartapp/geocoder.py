import requests

from django.conf import settings


def fetch_coordinates(address: str) -> tuple[float, float] | None:
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params=dict(geocode=address, apikey=settings.YANDEX_GEO_API, format="json"))
    response.raise_for_status()

    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    try:
        most_relevant = found_places[0]
    except IndexError:
        return None

    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")

    return lon, lat
