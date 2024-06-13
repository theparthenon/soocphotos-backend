"""Face recognition functions."""

import numpy as np
import requests


def get_face_encodings(image_path, known_face_locations):
    """Generate face encodings from the provided image path and known face locations."""

    json = {
        "source": image_path,
        "face_locations": known_face_locations,
    }
    face_encoding = requests.post(
        "http://localhost:8005/face-encodings", json=json, timeout=120
    ).json()

    face_encodings_list = face_encoding["encodings"]
    face_encodings = [np.array(enc) for enc in face_encodings_list]

    return face_encodings


def get_face_locations(image_path, model="hog"):
    """Given an image path and an optional model, this function returns the
    locations of all faces in the image using the specified model."""

    json = {"source": image_path, "model": model}
    face_locations = requests.post(
        "http://localhost:8005/face-locations", json=json, timeout=120
    ).json()
    return face_locations["face_locations"]
