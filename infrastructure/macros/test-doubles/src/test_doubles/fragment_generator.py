from typing import Any, Dict


class FragmentGenerator:
    @staticmethod
    def generate_fragment_from(fragment: Dict[str, Any], additional_resources: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Retrofit tests
        # TODO: Leave original fragment unchanged
        fragment['Resources'] = dict(**fragment['Resources'], **additional_resources)
        return fragment
