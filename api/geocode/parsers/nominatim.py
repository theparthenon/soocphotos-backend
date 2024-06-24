"""Functions for parsing Nominatim location data."""

from api.geocode import GEOCODE_VERSION


def parse(location):
    """Parses the location data into a GeoJSON object."""

    data = location.raw["address"]
    props = [
        "road",
        "town",
        "neighbourhood",
        "suburb",
        "hamlet",
        "borough",
        "city",
        "county",
        "state",
        "country",
    ]
    places = [data[prop] for prop in props if prop in data]
    center = [float(location.raw["lat"]), float(location.raw["lon"])]
    return {
        "features": [{"text": place, "center": center} for place in places],
        "places": places,
        "address": location.address,
        "center": center,
        "_v": GEOCODE_VERSION,
    }
