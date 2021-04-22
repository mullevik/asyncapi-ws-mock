from typing import Any, Dict, Callable, List
import logging

log = logging.getLogger(__name__)


def dereference(reference_path_string: str, full_specification: Dict):
    parts = reference_path_string.split("/")

    if parts[0] == "#":  # absolute reference
        current = full_specification
        for part in parts[1:]:
            current = current[part]

        return current

    # todo: more de-referencing options than the absolute one
    raise NotImplementedError


def validate_string(payload: Any, payload_specification: Dict):
    assert isinstance(payload, str)


def validate_integer(payload: Any, payload_specification: Dict):
    assert isinstance(payload, int)

    if "minimum" in payload_specification:
        assert payload >= payload_specification["minimum"]

    if "maximum" in payload_specification:
        assert payload <= payload_specification["maximum"]


def validate_float(payload: Any, payload_specification: Dict):
    assert isinstance(payload, float)


def validate_payload(payload: Any, payload_specification: Dict,
                     full_specification: Dict) -> True:
    """Recursively validates a payload of a message.
    :raises AssertionError when the payload is not valid
    :raises NotImplementedError when the payload contains properties,
    which are not yet supported by this validator
    :return True, when the payload is valid
    """
    if "type" not in payload_specification:
        # no type in specification -> look for $ref or oneOf

        if "$ref" in payload_specification:
            payload_specification = dereference(payload_specification["$ref"],
                                                full_specification)
        elif "oneOf" in payload_specification:

            oneOf_specifications = payload_specification["oneOf"]
            validation_results = [False for _ in oneOf_specifications]
            for i, spec in enumerate(oneOf_specifications):
                try:
                    validate_payload(payload, spec, full_specification)
                    validation_results[i] = True
                except AssertionError:
                    # AssertionErrors can happen and it is a desired behaviour
                    pass
            assert any(validation_results)
            return True

    # handle enum values (payload must be in the enum list)
    if "enum" in payload_specification:
        enum_values = payload_specification["enum"]
        assert payload in enum_values

    payload_type = payload_specification["type"]

    # handle different types
    if payload_type == "string":
        validate_string(payload, payload_specification)

    elif payload_type == "integer":
        validate_integer(payload, payload_specification)

    elif payload_type == "number":
        validate_float(payload, payload_specification)

    elif payload_type == "object":

        assert "properties" in payload_specification

        for prop in payload_specification["properties"].keys():
            assert prop in payload
            # recursive validation of each property
            validate_payload(payload[prop],
                             payload_specification["properties"][prop],
                             full_specification)
    else:
        # todo: do more types
        raise NotImplementedError
    return True


def _validate_message_second_step(message_data: Any,
                                  message_specification: Dict,
                                  full_specification: Dict) -> str:
    """
    :raises AssertionError if the message is not valid
    :raises NotImplementedError if the message contains data
    that are not yet supported by the validator
    :return value of the 'name' attribute of the message if the message is valid
    """
    # dereference message spec
    message_specification = message_specification \
        if "$ref" not in message_specification \
        else dereference(message_specification["$ref"], full_specification)

    payload_specification = message_specification["payload"]
    message_name = message_specification["name"]
    log.debug(f"Validating message: {message_data} "
              f"as message: {message_name} ...")
    validate_payload(message_data, payload_specification,
                     full_specification)
    return message_name


def validate_message(message_data: Any, message_specification: Dict,
                     full_specification: Dict) -> List[str]:
    """Recursively validates the content of the message.
    :return: List[str] - value of the 'name' attribute of each message,
    that passes the payload validation
    """
    output = []
    if "oneOf" in message_specification:

        message_specs = message_specification["oneOf"]

        for message_spec in message_specs:
            try:
                message_name = _validate_message_second_step(
                    message_data, message_spec, full_specification)
                output.append(message_name)
                log.debug(f"Message: {message_data} passed as {message_name}")
            except AssertionError:
                # do nothing if this message does not pass the validation
                log.debug(
                    f"Message: {message_data} does not pass a 'oneOf' validation")
    else:
        if "$ref" not in message_specification:
            message_specification = message_specification[
                next(iter(message_specification.keys()))]

        try:
            message_name = _validate_message_second_step(
                message_data, message_specification, full_specification)
            output.append(message_name)
            log.debug(f"Message: {message_data} passed as {message_name}")
        except AssertionError:
            # do nothing if this message does not pass the validation
            log.debug(f"Message: {message_data} does not pass validation")

    return output


def assert_throws_assertion_error(f: Callable):
    try:
        f()
    except AssertionError:
        assert True
    else:
        assert False


if __name__ == '__main__':
    # Payload assertions:

    ex_1_p = "hello world"

    assert validate_payload(ex_1_p, {"type": "string"}, None)
    assert_throws_assertion_error(lambda:
                                  validate_payload(ex_1_p, {"type": "integer"},
                                                   None))  # bad type

    ex_2_s = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "age": {
                "type": "integer"
            }
        }
    }
    assert validate_payload({"name": "Peter", "age": 20}, ex_2_s, None)
    assert_throws_assertion_error(lambda:
                                  validate_payload(
                                      {"name": "Peter", "age": "20"},
                                      ex_2_s, None))
    assert_throws_assertion_error(lambda:
                                  validate_payload(
                                      {"firstName": "Peter", "age": 20},
                                      ex_2_s, None))  # bad property name

    ex_3_s = {
        "$ref": "#/components/schemas/person"
    }
    ex_3_f = {
        "components": {
            "schemas": {
                "person": ex_2_s
            }
        }
    }

    assert validate_payload({"name": "John", "age": 30}, ex_3_s, ex_3_f)
    assert_throws_assertion_error(lambda:
                                  validate_payload({"name": 100, "age": 30},
                                                   ex_3_s,
                                                   ex_3_f))  # bad name

    ex_4_s = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "type": {
                "type": "string",
                "enum": ["cat", "dog"]
            },
            "weight": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100
            }
        }
    }

    assert validate_payload({"name": "Tom", "type": "cat", "weight": 5},
                            ex_4_s, None)
    assert_throws_assertion_error(lambda:
                                  validate_payload(
                                      {"name": "Paws", "type": "fox",
                                       "weight": 7},
                                      ex_4_s, None))  # bad animal type
    assert_throws_assertion_error(lambda:
                                  validate_payload(
                                      {"name": "Chonker", "type": "cat",
                                       "weight": 101},
                                      ex_4_s, None))  # bad weight

    ex_5_s = {
        "oneOf": [
            {"$ref": "#/components/schemas/person"},
            {"$ref": "#/components/schemas/animal"},
        ]
    }

    ex_5_f = {
        "components": {
            "schemas": {
                "person": ex_2_s,
                "animal": ex_4_s
            }
        }
    }

    assert validate_payload({"name": "John", "age": 30}, ex_5_s, ex_5_f)
    assert validate_payload({"name": "Tom", "type": "cat", "weight": 5},
                            ex_5_s, ex_5_f)
    assert_throws_assertion_error(lambda:
                                  validate_payload(
                                      {"name": "Ghost", "type": "dog",
                                       "weight": -1}, ex_5_s,
                                      ex_5_f))  # bad weight

    # Message assertions:

    ex_6_s = {
        "person_message": {
            "name": "PersonMessage",
            "payload": ex_2_s,
        }
    }

    assert "PersonMessage" in validate_message({"name": "Postman", "age": 42},
                                               ex_6_s, None)
    assert len(
        validate_message({"name": "Jumper", "type": "dog", "weight": 25},
                         ex_6_s, None)
    ) == 0  # wrong message

    ex_7_s = {
        "oneOf": [
            {"name": "PersonMessage", "payload": ex_2_s},
            {"$ref": "#/components/messages/animal_message"},
        ]
    }

    ex_7_f = {
        "components": {
            "messages": {
                "animal_message": {
                    "name": "AnimalMessage",
                    "payload": {
                        "$ref": "#/components/schemas/animal"
                    }
                },
            },
            "schemas": {
                "person": ex_2_s,
                "animal": ex_4_s
            }
        }
    }

    assert "PersonMessage" in validate_message(
        {"name": "Postman", "age": 42}, ex_7_s, ex_7_f)
    assert "AnimalMessage" not in validate_message(
        {"name": "Postman", "age": 42}, ex_7_s, ex_7_f)

    assert "AnimalMessage" in validate_message(
        {"name": "Jumper", "type": "dog", "weight": 25}, ex_7_s, ex_7_f)
    assert "PersonMessage" not in validate_message(
        {"name": "Jumper", "type": "dog", "weight": 25}, ex_7_s, ex_7_f)

    assert len(
        validate_message({"name": "Ghost", "type": "dog", "weight": -1},
                         ex_7_s, ex_7_f)
    ) == 0  # bad weight -> wrong message
