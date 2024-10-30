import json
from copy import deepcopy

SECOND_SUBSTITUTION_PREFIX = '!SecondSub '
SECOND_SUBSTITUTION_PREFIX_LENGTH = len(SECOND_SUBSTITUTION_PREFIX)


def handler(event, _):
    print(f'Received event: {json.dumps(event)}')

    original_fragment = event['fragment']
    print(f'Received fragment: {json.dumps(original_fragment)}')

    updated_fragment = deepcopy(original_fragment)

    updated_fragment['Resources'] = expand_second_substitutions(original_fragment['Resources'])

    print(f'Returning fragment: {json.dumps(updated_fragment)}')
    return create_response(event, updated_fragment)


def expand_second_substitutions(node: any):
    if type(node) is dict:
        accumulator = {}

        for key, value in node.items():
            accumulator[key] = expand_second_substitutions(value)

        return accumulator

    if type(node) is list:
        accumulator = []

        for item in node:
            accumulator = accumulator + [expand_second_substitutions(item)]

        return accumulator

    if type(node) is str and node.startswith(SECOND_SUBSTITUTION_PREFIX):
        return {
            'Fn::Sub': node[SECOND_SUBSTITUTION_PREFIX_LENGTH:].replace("@{", "${")
        }

    return node


def create_response(event, updated_fragment):
    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }
