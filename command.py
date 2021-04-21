import argparse
import json
import logging
import time
from typing import List, Dict

import gevent
from geventwebsocket import WebSocketServer

from message import dereference, validate_message

log = logging.getLogger(__name__)


class MockedWebSocketServer(WebSocketServer):
    """Just a helper class for type hinting."""
    specification: Dict
    events: Dict
    valid_command_chain_time: float
    args: argparse.Namespace


class Commands:
    WAIT = "wait"
    BROADCAST_EXAMPLE = "broadcast_example"
    STOP_COMMAND_CHAINS = "stop_command_chains"

    @staticmethod
    def execute_wait(command: Dict, server: MockedWebSocketServer,
                     **kwargs) -> Dict:
        log.debug(f"Executing command WAIT for {command['seconds']} seconds")
        gevent.sleep(command["seconds"])
        return {}

    @staticmethod
    def execute_broadcast_example(command: Dict, server: MockedWebSocketServer,
                                  **kwargs) -> Dict:
        log.debug(f"Executing command BROADCAST_EXAMPLE "
                  f"with example: {command['example_ref']}")

        example = dereference(command["example_ref"], server.specification)
        example_data = example["value"]

        messages = validate_message(example_data,
                                    server.specification[
                                        "channels"][command["channel"]][
                                        "subscribe"]["message"],
                                    server.specification)

        if len(messages) == 0:
            log.error(f"Provided example {command['example_ref']} is not valid"
                      f"in any subscribe message specification "
                      f"for channel {command['channel']}")
            if server.args.strict:
                log.info("Mock server is going to terminate because of the "
                         "--strict argument")
                exit(3)
            else:
                log.warning(f"Example {command['example_ref']} will be sent "
                            f"even though it is not a valid subscribe message "
                            f"(use --strict to force the validation)")

        for client in server.clients.values():

            channel_path = client.ws.path

            if channel_path.replace("/", "") == command["channel"].replace("/", ""):
                client.ws.send(json.dumps(example_data))
                log.debug(f"Sent example {command['example_ref']} to a client "
                          f"using channel {command['channel']}")
        return {}

    @staticmethod
    def execute_stop_command_chains(command: Dict,
                                    server: MockedWebSocketServer,
                                    **kwargs) -> Dict:
        log.debug("Executing command chain stop")
        server.valid_command_chain_time = time.time()
        return {
            "start_time": time.time()
        }


def execute_command(command: Dict, server: MockedWebSocketServer) -> Dict:
    command_name = next(iter(command.keys()))
    command_data = command[command_name]

    if command_name == Commands.WAIT:
        return Commands.execute_wait(command_data, server)
    elif command_name == Commands.BROADCAST_EXAMPLE:
        return Commands.execute_broadcast_example(command_data, server)
    elif command_name == Commands.STOP_COMMAND_CHAINS:
        return Commands.execute_stop_command_chains(command_data, server)
    else:
        # todo: More commands in the future
        raise NotImplementedError(
            f"Command {command_name} is not implemented in this version")


def execute_commands(commands: List[Dict], server: MockedWebSocketServer) -> None:
    start_time = time.time()

    for i, command in enumerate(commands):
        if start_time > server.valid_command_chain_time:
            output = execute_command(command, server)
            if "start_time" in output:
                start_time = output["start_time"]
        else:
            log.debug(f"Command chain stopped execution prematurely "
                      f"after {i} executions from {len(commands)}")
            break


def execute(commands: List[Dict], server: MockedWebSocketServer) -> None:
    gevent.spawn(execute_commands, commands=commands, server=server)
