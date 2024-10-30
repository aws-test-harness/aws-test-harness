#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

usage() {
  echo "Usage: $0 [--help] [--macros-stack-name stack_name] [--stack-templates-s3-uri s3_uri]"
  exit 1
}

while [[ "${1:-}" != "" ]]; do
    case ${1} in
        --help )
            usage
            ;;
        --macros-stack-name )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --macros-stack-name"
              usage
            fi

            macros_stack_name="${1}"
            ;;
        --stack-templates-s3-uri )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --stack-templates-s3-uri"
              usage
            fi

            stack_templates_s3_uri="${1}"
            ;;
        * )
            echo "Unknown option: ${1}"
            usage
            ;;
    esac
    shift
done

if [ -z "${macros_stack_name:-}" ]; then
  echo "Missing required argument: --macros-stack-name"
  usage
fi

if [ -z "${stack_templates_s3_uri:-}" ]; then
  echo "Missing required argument: --stack-templates-s3-uri"
  usage
fi

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}"

echo "Deploying macros..."
aws cloudformation deploy \
  --stack-name "${macros_stack_name}" \
  --template-file macros.yaml \
  --capabilities CAPABILITY_IAM

echo "Deploying stack templates..."
aws s3 sync \
  templates \
  "${stack_templates_s3_uri}"