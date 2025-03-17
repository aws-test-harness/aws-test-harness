#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

stack_name=$1
code_s3_bucket=$2
code_s3_key_prefix=$3
macro_name_prefix=$4

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

source "${script_directory_path}/install.env"

echo "Uploading assets..."

aws s3 sync \
  "${script_directory_path}/assets" \
  "s3://${code_s3_bucket}/${code_s3_key_prefix}"

echo "Deploying infrastructure..."

aws cloudformation deploy \
  --template-file "${script_directory_path}/template.yaml" \
  --stack-name "${stack_name}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    MacroNamePrefix="${macro_name_prefix}" \
    CodeS3Bucket="${code_s3_bucket}" \
    TestDoublesMacroCodeS3Key="${code_s3_key_prefix}${TEST_DOUBLES_MACRO_CODE_BUNDLE_PATH}" \
    TestDoubleInvocationHandlerFunctionCodeS3Key="${code_s3_key_prefix}${TEST_DOUBLE_INVOCATION_HANDLER_FUNCTION_CODE_BUNDLE_PATH}"