import json
import logging
import os
from typing import List, Iterable, Dict

from geventwebsocket import WebSocketApplication

from command import execute
from events import EventTypes
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

    def _get_events_by_type(self, event_type: str) -> List[Dict]:
        out = []
        for event_name, event in self.protocol.server.events["events"].items():

            if event["channel"].replace("/", "") == self.ws.path.replace("/", "")\
                    and event["when"] == event_type:
                event["name"] = event_name
                out.append(event)
        return out

    def on_open(self):
        log.debug("New client joined")

    def _get_events_for_messages(self, message_names: List[str]) -> Iterable[Dict]:
        events = self._get_events_by_type(EventTypes.MESSAGE_RECEIVED)
        return filter(lambda e: any(
            [e["message_name"] == m for m in message_names]
        ), events)

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
            if self.protocol.server.args.strict:
                log.info("Mock server is going to terminate because of the "
                         "--strict argument")
                exit(3)
            else:
                log.warning(f"Received message is not a valid publish message "
                            f"for channel {self.ws.path}. The server will "
                            f"continue listening, however no message_received "
                            f"event will be triggered (use --strict to "
                            f"terminate this server in this situation)")
        else:
            log.info(f"Following messages passed validation for sent data: {messages}")

        events = self._get_events_for_messages(messages)

        for event in events:
            log.info(f"Executing command chain {event['name']}")
            execute(event["do"], self.protocol.server)

    def on_close(self, reason):
        log.debug("Client has disconnected")