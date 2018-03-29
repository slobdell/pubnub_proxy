import base64
from collections import defaultdict
import json
import time
import threading
import time
import uuid

from flask import Flask, Response
from flask import request
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory

SUBSCRIBE_KEY = os.environ["SUBSCRIBE_KEY"]
PUBLISH_KEY = os.environ["PUBLISH_KEY"]

TX_CHANNEL = "channelTX"
MAX_RETRIES = 8

request_pool = {}
response_rebuilder = defaultdict(list)
app = Flask(__name__)


def deduped_chunks(chunks):
    return {item["chunk_index"]: item for item in chunks}.values()


def get_setup_pubnub():

    class SubCallback(SubscribeCallback):

        def presence(self, pubnub, presence):
            pass

        def status(self, pubnub, status):
            pass

        def message(self, pubnub, message):
            message_dict = message.message
            request_id = uuid.UUID(message_dict["request_id"])
            response_rebuilder[request_id].append(message_dict)

            deduped = deduped_chunks(response_rebuilder[request_id])
            if len(deduped) == message_dict["chunks"]:
                deduped.sort(
                    key=lambda item: item["chunk_index"],
                )
                response_content = base64.urlsafe_b64decode(
                    str(
                        "".join([d["response_content"] for d in deduped])
                    )
                )
                request_pool[request_id] = response_content
                del response_rebuilder[request_id]

    pnconfig = PNConfiguration()
    pnconfig.subscribe_key = SUBSCRIBE_KEY
    pnconfig.publish_key = PUBLISH_KEY
    pnconfig.ssl = False

    pubnub = PubNub(pnconfig)

    callback = SubCallback()
    pubnub.add_listener(callback)
    pubnub.subscribe().channels('channelRX').execute()
    # pubnub.unsubscribe_all()
    # pubnub.stop()
    return pubnub

PN = get_setup_pubnub()


def publish_pubnub_message(pubnub, root_url, request_method="GET", post_dict=None):
    request_id = uuid.uuid4()
    request_pool[request_id] = None

    payload_dict = {
        "request_id": str(request_id),
        "method": request_method,
        "root_url": root_url,
        "data": post_dict or {},
    }

    publish_timestamp = time.time()
    _publish(pubnub, payload_dict)
    retry_period = 0.8
    retry_count = 0

    while request_pool[request_id] == None:
        if retry_count > MAX_RETRIES:
            break
        now = time.time()
        if now - publish_timestamp > retry_period:
            _publish(pubnub, payload_dict)
            retry_period *= 2
            publish_timestamp = now
            retry_count += 1
        time.sleep(0)

    response_content = request_pool[request_id]
    del request_pool[request_id]
    return response_content


def _publish(pubnub, serialized):
    pubnub.publish().channel(
        TX_CHANNEL,
    ).message(
        serialized,
    ).sync()


@app.route('/')
def index():
    return publish_pubnub_message(PN, "/")


@app.route('/test/')
def index2():
    return publish_pubnub_message(PN, "/")


@app.route('/staticx/<path:path>', methods=["GET"])
def send_static(path):
    return publish_pubnub_message(PN, "/staticx/%s" % path)


@app.route('/api/zone_settings/', methods=['GET', 'POST'])
def receive_user_input():
    return publish_pubnub_message(
        PN,
        "/api/zone_settings/",
        request_method=request.method,
        post_dict=request.json,
    )


@app.route('/api/download/', methods=['GET'])
def download():
    return Response(
        publish_pubnub_message(PN, "/api/download/"),
        mimetype="text/plain",
        headers={
            "Content-disposition": "attachment; filename=settings.lightwav"
        }
    )


@app.route('/api/upload/', methods=['POST'])
def upload():
    publish_pubnub_message(
        PN,
        "/api/put_settings/",
        request_method=request.method,
        post_dict={
            "obfuscated": request.files['file'].stream.read(),
        },
    )
    return "", 204


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3001)
