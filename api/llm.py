"""Generate prompt for LLM model."""

import logging.handlers

from django.conf import settings
import requests

logger = logging.getLogger("llm")


def generate_prompt(prompt):
    """Generate prompt for LLM model."""

    if settings.LLM_MODEL == "none":
        return None
    if settings.LLM_MODEL == "mistral-7b-v0.1.Q5_K_M":
        model_path = "/protected_media/data_models/mistral-7b-v0.1.Q5_K_M.gguf"
    if settings.LLM_MODEL == "mistral-7b-instruct-v0.2.Q5_K_M":
        model_path = "/protected_media/data_models/mistral-7b-instruct-v0.2.Q5_K_M.gguf"

    json = {
        "model_path": model_path,
        "max_tokens": 64,
        "prompt": prompt,
    }
    caption_response = requests.post("http://localhost:8008/", json=json).json()

    print(caption_response)

    return caption_response["prompt"]["choices"][0]["text"]
