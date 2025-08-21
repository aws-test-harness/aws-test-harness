#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail;

usage() {
  echo "Usage: $0 [--help] --macros-stack-name stack_name --stack-templates-s3-uri s3_uri --aws-region region [--macro-names-prefix macro_names_prefix] [--image-repository-names-prefix image_repository_names_prefix]"
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
        --macro-names-prefix )
            shift
            macro_names_prefix="${1:-}"
            ;;
        --image-repository-names-prefix )
            shift
            image_repository_names_prefix="${1:-}"
            ;;
        --stack-templates-s3-uri )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --stack-templates-s3-uri"
              usage
            fi

            stack_templates_s3_uri="${1}"
            ;;
        --aws-region )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --aws-region"
              usage
            fi

            aws_region="${1}"
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

if [ -z "${aws_region:-}" ]; then
  echo "Missing required argument: --aws-region"
  usage
fi

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd "${script_directory_path}"

echo "Deploying macros..."
aws cloudformation deploy \
  --stack-name "${macros_stack_name}" \
  --template-file macros.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides MacroNamesPrefix="${macro_names_prefix}" ImageRepositoryNamesPrefix="${image_repository_names_prefix}"

repository_uri=$(aws cloudformation describe-stacks \
  --stack-name "${macros_stack_name}" \
  --query 'Stacks[0].Outputs[?OutputKey==`ECSTaskContainerRepositoryUri`].OutputValue' \
  --output text)

if [ -z "${repository_uri}" ]; then
  echo "ERROR: Could not retrieve ECS task repository URI from CloudFormation stack ${macros_stack_name}"
  exit 1
fi

echo "Building and pushing ECS task test double Docker image..."
account_id=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "${aws_region}" | docker login --username AWS --password-stdin "${account_id}.dkr.ecr.${aws_region}.amazonaws.com"

cd ecs-task-test-double
docker build --platform linux/arm64 -t "${repository_uri}" .
docker push "${repository_uri}"
cd ..

working_directory_path=$(mktemp -d)

cp -r templates/* "${working_directory_path}"

cd "${working_directory_path}"

# Specify in-place backup extentions so sed works on both Linux and macOS
sed -i.original "s/__MACRO_NAMES_PREFIX__/${macro_names_prefix}/" ./*
rm ./*.original

echo "Deploying stack templates..."
aws s3 sync . "${stack_templates_s3_uri}"