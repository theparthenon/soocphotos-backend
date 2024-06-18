"""Main image similarity service functions."""

import json
from urllib.error import URLError

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from gevent.pywsgi import WSGIServer

from retrieval_index import RetrievalIndex  # pylint: disable=import-error
from utils import logger  # pylint: disable=import-error

app = Flask(__name__)
api = Api(app)

index = RetrievalIndex()


class BuildIndex(Resource):
    """Builds the image similarity index for a specific user."""

    def post(self):
        """Receives the image hashes and embeddings for a specific user and builds the index."""

        request_body = json.loads(request.data)

        user_id = request_body["user_id"]
        image_hashes = request_body["image_hashes"]
        image_embeddings = request_body["image_embeddings"]

        index.build_index_for_user(user_id, image_hashes, image_embeddings)

        return jsonify({"status": True, "index_size": index.indices[user_id].ntotal})

    def delete(self):
        """Deletes the index for a specific user."""

        user_id = json.loads(request.data)["user_id"]
        if user_id not in index.indices:
            return jsonify({"status": True})
        del index.indices[user_id]
        del index.image_hashes[user_id]
        return jsonify({"status": True})


class SearchIndex(Resource):
    """Searches the image similarity index for a specific user."""

    def post(self):
        """Receives the image embedding for a specific user and searches the index."""

        try:
            request_body = json.loads(request.data)

            user_id = request_body["user_id"]
            image_embedding = request_body["image_embedding"]
            if "n" in request_body.keys():
                n = int(request_body["n"])
            else:
                n = 100

            if "threshold" in request_body.keys():
                thres = float(request_body["threshold"])
            else:
                thres = 27.0

            res = index.search_similar(user_id, image_embedding, n, thres)

            return jsonify({"status": True, "result": res})
        except URLError as e:
            logger.error(str(e))
            return jsonify({"status": False, "result": []}), 500


class Health(Resource):
    """Services health check."""

    def get(self):
        """Returns the health of the service."""

        return jsonify({"status": True})


api.add_resource(BuildIndex, "/build/")
api.add_resource(SearchIndex, "/search/")
api.add_resource(Health, "/health/")


def start_server():
    """Starts the image similarity service on port 8002."""

    logger.info("Starting server")
    server = WSGIServer(("0.0.0.0", 8002), app)
    server.serve_forever()


if __name__ == "__main__":
    start_server()
