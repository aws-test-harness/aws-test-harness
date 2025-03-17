import os


def absolute_path_relative_to(anchor_file: str, *relative_file_path_parts: str) -> str:
    return os.path.normpath(os.path.join(
        os.path.dirname(anchor_file),
        *relative_file_path_parts
    ))
