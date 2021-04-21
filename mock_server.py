import argparse
import logging
import os
import time
from collections import OrderedDict

import gevent
from yaml import Loader, load
from geventwebsocket import WebSocketServer, Resource

from channel import ChannelApplication

log = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SequenceEmitter')

    parser.add_argument('specification_file', action="store", type=str)
    parser.add_argument('events_file', action="store", type=str)
    parser.add_argument('-p', '--port', action="store", dest="port",
                        type=int, default="8080")
    parser.add_argument('--strict', action="store_true", default=False)
    args = parser.parse_args()

    logging.basicConfig(format='[%(asctime)s] %(levelname).1s - %(message)s',
                        level=logging.DEBUG)

    with open(args.specification_file, "r") as specification_file:
        specification = load(specification_file, Loader=Loader)

    with open(args.events_file, "r") as events_file:
        events = load(events_file, Loader=Loader)

    channels = [os.path.join("/", channel_name)
                for channel_name in specification["channels"].keys()]

    host = "0.0.0.0"
    server = WebSocketServer(
        (host, args.port),
        Resource(OrderedDict([(channel, ChannelApplication)
                              for channel in channels]))
    )
    server.specification = specification
    server.events = events
    server.valid_command_chain_time = time.time()
    server.args = args
    log.info(f"Started AsyncApi-WebSocket-Mock server at {host}:{args.port}")
    server.serve_forever()
