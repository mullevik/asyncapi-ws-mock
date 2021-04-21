import json
import logging
import os

from geventwebsocket import WebSocketApplication

from message import validate_message

log = logging.getLogger(__name__)


class ChannelApplication(WebSocketApplication):

    def __init__(self, ws):
        super().__init__(ws)

        specification = self.protocol.server.specification
        channel_names = {os.path.join("/", spec_channel): spec_channel
                         for spec_channel in specification["channels"].keys()}

        spec_channel = channel_names[self.ws.path]
        self.specification = specification["channels"][spec_channel]

        log.info(f"Initialized WS channel {self.ws.path} ({spec_channel})")

    def on_open(self):
        log.debug("New client joined")

    def on_message(self, message, **kwargs):
        log.debug(f"{self.ws.path} - received a message: {message}")
        data = json.loads(message)

        try:
            message_specification = self.specification["publish"]["message"]
        except KeyError:
            log.error(f"{self.ws.path} - "
                      f"There is no publish configuration for incoming messages")
            raise ValueError

        messages = validate_message(data, message_specification,
                                    self.protocol.server.specification)

        if len(messages) == 0:
            log.error(f"Sent data did not pass validation "
                      f"for any of the specified messages")
            exit(2)
        else:
            log.info(f"Following messages passed validation for sent data: {messages}")

    def on_close(self, reason):
        log.debug("Client has disconnected")