import base64
import math
import os
import sys

from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory
import requests


SUBSCRIBE_KEY = os.environ["SUBSCRIBE_KEY"]
PUBLISH_KEY = os.environ["PUBLISH_KEY"]
MESSAGE_CHUNK_SIZE = 16 * 1024


pnconfig = PNConfiguration()
pnconfig.subscribe_key = SUBSCRIBE_KEY
pnconfig.publish_key = PUBLISH_KEY
pnconfig.ssl = False

pubnub = PubNub(pnconfig)

SUBSCRIBE_CHANNEL = "channelTX"
RESPONSE_CHANNEL = "channelRX"

class Context(object):
    target_port = 99


def my_publish_callback(envelope, status):
    # Check whether request successfully completed or not
    if not status.is_error():
        pass  # Message successfully published to specified channel.
    else:
        pass  # Handle message publish error. Check 'category' property to find out possible issue
        # because of which request did fail.
        # Request can be resent using: [status retry];


class SubCallback(SubscribeCallback):

    def presence(self, pubnub, presence):
        pass

    def status(self, pubnub, status):
        pass

    def message(self, pubnub, message):
        message_dict = message.message
        url = message_dict["root_url"]
        full_url = "http://127.0.0.1:%s%s" % (Context.target_port, url)
        if message_dict["method"] == "GET":
            response = requests.get(full_url)
        elif message_dict["method"] == "POST":
            response = requests.post(full_url, json=message_dict["data"])

        all_response_content = base64.urlsafe_b64encode(response.content)
        num_chunks = int(math.ceil(float(len(all_response_content)) / MESSAGE_CHUNK_SIZE))

        cursor = 0
        for index in xrange(num_chunks):
            content_chunk = all_response_content[cursor: cursor + MESSAGE_CHUNK_SIZE]
            cursor += MESSAGE_CHUNK_SIZE
            pubnub.publish().channel(RESPONSE_CHANNEL).message({
                "request_id": message_dict["request_id"],
                "response_content": content_chunk,
                "chunks": num_chunks,
                "chunk_index": index,
            }).async(my_publish_callback)


if __name__ == "__main__":
    Context.target_port = int(sys.argv[1])

    pubnub.add_listener(SubCallback())
    pubnub.subscribe().channels(SUBSCRIBE_CHANNEL).execute()
