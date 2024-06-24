# pylint: disable=W1404
"""Functions for parsing OpenCage location data."""

from api.geocode import GEOCODE_VERSION


def parse(location):
    """Parses the location data into a GeoJSON object."""

    data = location.raw["components"]
    center = [location.raw["geometry"]["lat"], location.raw["geometry"]["lng"]]
    props = [
        data["_type"],
        "road",
        "suburb",
        "municipality",
        "hamlet",
        "town" "city",
        "borough",
        "state",
        "county",
        "country",
    ]
    places = [data[prop] for prop in props if prop in data]
    return {
        "features": [{"text": place, "center": center} for place in places],
        "places": places,
        "address": location.address,
        "center": center,
        "_v": GEOCODE_VERSION,
    }
