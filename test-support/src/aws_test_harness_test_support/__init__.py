import json
import os
from typing import cast, Dict


def load_test_configuration() -> Dict[str, str]:
    configuration_file_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../config.json'))

    with open(configuration_file_path, 'r') as f:
        return cast(Dict[str, str], json.load(f))
