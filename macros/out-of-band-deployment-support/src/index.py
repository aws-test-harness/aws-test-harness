import copy
import json
from uuid import uuid4


def handler(event, _):
    original_fragment = event['fragment']

    enabled = event['params'].get('Enabled', 'false')

    if enabled != 'true':
        return create_response(event, original_fragment)

    print(f'Received fragment: {json.dumps(original_fragment)}')

    updated_fragment = copy.deepcopy(original_fragment)

    resource_type = original_fragment.get('Type')

    if resource_type in ['AWS::StepFunctions::StateMachine', 'AWS::Serverless::StateMachine']:
        original_definition_substitutions = original_fragment['Properties'].get('DefinitionSubstitutions', {})

        updated_fragment['Metadata'] = {
            **original_fragment.get('Metadata', {}),
            **{'DefinitionSubstitutions': original_definition_substitutions}
        }

        original_properties = original_fragment['Properties']

        updated_fragment['Properties'] = {
            **original_properties,
            **{
                'DefinitionSubstitutions': {
                    **original_definition_substitutions,
                    **{'RandomDataToForceFlushingDefinition': str(uuid4())}
                }
            }
        }

        print(f'Returning fragment: {json.dumps(updated_fragment)}')
        return create_response(event, updated_fragment)


def create_response(event, updated_fragment):
    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }


def get_definition_substitutions(original_fragment):
    return original_fragment['Properties'].get('DefinitionSubstitutions', {})
