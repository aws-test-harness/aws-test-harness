#!/usr/bin/env bash

# TODO: Retrofit install script and infrastructure tests

stack_templates_s3_uri=$1

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

aws s3 sync "${script_directory_path}/../templates" "${stack_templates_s3_uri}"