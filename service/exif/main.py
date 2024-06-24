import exiftool
import gevent
import logging.handlers
from flask import Flask, request
from gevent.pywsgi import WSGIServer

from django.conf import settings

logger = logging.getLogger("exif")


static_et = exiftool.ExifTool()
static_struct_et = exiftool.ExifTool(common_args=["-struct"])

app = Flask(__name__)


def log(message):
    logger.info("exif: %s", message)


@app.route("/get-tags", methods=["POST"])
def get_tags():
    try:
        data = request.get_json()
        files_by_reverse_priority = data["files_by_reverse_priority"]
        tags = data["tags"]
        struct = data["struct"]
    except Exception as e:
        logger.error("An error occurred: %s", e)
        return "", 400

    et = None
    if struct:
        et = static_struct_et
    else:
        et = static_et
    if not et.running:
        et.start()

    values = []
    try:
        for tag in tags:
            value = None
            for file in files_by_reverse_priority:
                retrieved_value = et.get_tag(tag, file)
                if retrieved_value is not None:
                    value = retrieved_value
            values.append(value)
    except Exception as e:
        logger.error("An error occurred: %s", e)

    return {"values": values}, 201


@app.route("/health", methods=["GET"])
def health():
    return {"status": "OK"}, 200


if __name__ == "__main__":
    log("Exif service starting")
    server = WSGIServer(("0.0.0.0", 8010), app)
    server_thread = gevent.spawn(server.serve_forever)
    gevent.joinall([server_thread])
