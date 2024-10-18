import copy
import json


def handler(event, _):
    original_fragment = event['fragment']
    print(f'Received fragment: {json.dumps(original_fragment)}')

    updated_fragment = copy.deepcopy(original_fragment)

    resource_type = original_fragment.get('Type')

    if resource_type in ['AWS::StepFunctions::StateMachine', 'AWS::Serverless::StateMachine']:
        updated_fragment['Metadata'] = {
            **original_fragment.get('Metadata', {}),
            **{'DefinitionSubstitutions': original_fragment.get('Properties', {}).get('DefinitionSubstitutions', {})}
        }

    print(f'Returning fragment: {json.dumps(updated_fragment)}')

    return {
        "requestId": event['requestId'],
        "status": "success",
        "fragment": updated_fragment
    }


