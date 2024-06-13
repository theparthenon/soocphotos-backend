"""Sends image to image captioning model."""

import requests


def generate_caption(image_path, onnx, blip):
    """Send data to image captioning model to generate caption."""

    json = {
        "image_path": image_path,
        "onnx": onnx,
        "blip": blip,
    }
    caption_response = requests.post(
        "http://localhost:8007/generate-caption", json=json, timeout=120
    ).json()

    return caption_response["caption"]


def unload_model():
    """Unload image captioning model"""

    requests.get("http://localhost:8007/unload-model", timeout=120)


def export_onnx(encoder_path, decoder_path):
    """Export the encoder and decoder models to ONNX format."""

    json = {
        "encoder_path": encoder_path,
        "decoder_path": decoder_path,
    }
    requests.get("http://localhost:8007/export-onnx", json=json, timeout=120)
