# AsyncAPI WebSocket server mock
Simple mock server which sends and receives WebSocket messages according to provided [AsyncAPI](https://www.asyncapi.com/docs/getting-started) specification.

1. specify API using [AsyncAPI](https://www.asyncapi.com/docs/getting-started)
2. configure what should the mock do when it encounters a message
3. run your WebSocket frontend against this mocked server


## Install

Directly:
```
git clone git@github.com:mullevik/asyncapi-ws-mock
cd asyncapi-ws-mock

python -m venv env
source env/bin/activate
pip install requirements
```

Or build a docker image using local ```Dockerfile```:

```
docker build . -t asyncapi-ws-mock
```

## Specify API

Learn how to write AsyncAPI [here](https://www.asyncapi.com/docs/getting-started).

An example ```specification.yaml``` file can look like this:
```yaml
asyncapi: 2.0.0
info:
  title: Example specification
  version: '0.1.0'

servers:
  local:
    url: "http://localhost:8080"
    protocol: ws
    description: Local mocked server

channels:
  chat:
    publish:
      message:
        $ref: '#/components/messages/text_message'
    
    subscribe:
      message:
        $ref: '#/components/messages/text_message'

components:
  messages:
    text_message:
      name: TextMessage
      description: User sends text to the chat
      payload:
        type: string
      examples:
        simple_message:
          summary: Hello world chat message
          value: "Hello World"
        long_message:
          summary: Long chat message
          value: "The quick brown fox jumps over the lazy dog"
```

## Specify mocked events

Define what should the mocked server do when an event happens.

An example ```events.yaml``` file can look like this:

```yaml
events:

  received_chat_message:
    when: message_received
    message_name: TextMessage
    channel: chat

    do:
      - broadcast_example:
          channel: chat
          example_ref: '#/components/messages/text_message/examples/simple_message'
      - wait:
          seconds: 2
      - broadcast_example:
          channel: chat
          example_ref: '#/components/messages/text_message/examples/long_message'
```

This example can be interpreted like so: _Whenever a message is received in the channel ```chat``` and the message has a structure of ```TextMessage```, broadcast ```simple_message``` example message to all clients connected to channel ```chat```. Then wait 2 seconds and after that broadcast another example (this time ```long_message```) message to all clients connected to channel ```chat```._

## Run the server

```
python mock_server.py example-config/specification.yaml example-config/events.yaml
```
#### Additional attributes
- ```-p [int]```, ```--port [int]``` - specify your favorite port (default is 8080)
- ```--strict``` - exit when a validation error is raised (when the structure of a message is not according to the specification) (default behaviour is just a warning output message)
- ```--debug``` - sets the ```logging``` level to ```logging.DEBUG``` (default is ```logging.INFO```)


### Run with docker

Run local container with ```example-config``` passed as a volume and redirected port:
```
docker run --rm -v $(pwd)/example-config:/app/config -p 40001:8080 -it asyncapi-ws-mock
```

Note that the app inside the  container always loads files ```/app/config/specification.yaml``` and ```/app/config/events.yaml``` and listens on port ```8080```.

Additional arguments can be passed to the container like so:
```
docker run --rm -v $(pwd)/example-config:/app/config -p 40001:8080 -it asyncapi-ws-mock --strict --debug
```