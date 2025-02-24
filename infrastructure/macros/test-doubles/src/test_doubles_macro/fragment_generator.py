from typing import Any, Dict


class FragmentGenerator:
    @staticmethod
    def generate_fragment_from(fragment: Dict[str, Any], additional_resources: Dict[str, Any]) -> Dict[str, Any]:
        return dict(
            **{key: value for key, value in fragment.items() if key != 'Resources'},
            Resources=dict(**fragment['Resources'], **additional_resources)
        )
