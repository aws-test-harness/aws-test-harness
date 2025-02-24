from logging import getLogger
from typing import Any, TypedDict, Dict, NotRequired

from test_doubles_macro.fragment_generator import FragmentGenerator
from test_doubles_macro.test_double_resource_factory import TestDoubleResourceFactory

LOGGER = getLogger()


class CloudFormationMacroEvent(TypedDict):
    requestId: str
    accountId: str
    region: str
    fragment: Dict[str, Any]
    templateParameterValues: Dict[str, Any]


class CloudFormationMacroResponse(TypedDict):
    requestId: str
    status: str
    fragment: Dict[str, Any]
    errorMessage: NotRequired[str]


def handler(event: CloudFormationMacroEvent, _: Any) -> CloudFormationMacroResponse:
    original_fragment = event['fragment']

    LOGGER.info("Received CloudFormation template fragment", extra=dict(fragment=original_fragment))

    additional_resources = TestDoubleResourceFactory.generate_additional_resources(event['templateParameterValues'])

    updated_fragment = FragmentGenerator.generate_fragment_from(original_fragment, additional_resources)

    LOGGER.info("Returning updated CloudFormation template fragment", extra=dict(fragment=updated_fragment))

    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }
