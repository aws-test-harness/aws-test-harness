#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

stack_name=$1
code_s3_bucket=$2
code_s3_key_prefix=$3
macro_name_prefix=$4

script_directory_path="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

get_absolute_path() {
  local relative_path="$1"
  echo "${script_directory_path}/../${relative_path}"
}

distributable_directory_path="$(get_absolute_path dist)"

get_lambda_function_distributable_directory_path() {
  local lambda_function_directory_relative_path="$1"
  echo "${distributable_directory_path:?}/${lambda_function_directory_relative_path}"
}

build_lambda_function_code_bundle() {
  local lambda_function_directory_relative_path="$1"

  echo "Building Lambda function code bundle for ${lambda_function_directory_relative_path}..." 1>&2

  local working_directory_path
  working_directory_path="$(mktemp -d)"
  cp -r "$(get_absolute_path "${lambda_function_directory_relative_path}")/src/" "${working_directory_path}"
  find "${working_directory_path}" -exec touch -t 198001010000 {} +

  local code_bundle_temp_file_path
  code_bundle_temp_file_path="$(mktemp).zip"

  pushd "${working_directory_path}" > /dev/null
  zip -qr "${code_bundle_temp_file_path}" .
  popd > /dev/null

  touch -t 198001010000 "${code_bundle_temp_file_path}"

  local lambda_function_distributable_directory
  lambda_function_distributable_directory="$(get_lambda_function_distributable_directory_path "${lambda_function_directory_relative_path}")"
  rm -rf "${lambda_function_distributable_directory}"
  mkdir -p "${lambda_function_distributable_directory}"

  local code_bundle_checksum
  code_bundle_checksum="$(cksum "${code_bundle_temp_file_path}" | cut -f 1 -d ' ')"

  local code_bundle_file_name
  code_bundle_file_name="${code_bundle_checksum}.zip"
  mv "${code_bundle_temp_file_path}" "${lambda_function_distributable_directory}/${code_bundle_file_name}"

  echo "${code_bundle_file_name}"
}

upload_lambda_function_code_bundle() {
  local lambda_function_directory_relative_path="$1"
  local lambda_function_code_bundle_file_name="$2"

  echo "Uploading Lambda function code bundle for ${lambda_function_directory_relative_path}..." 1>&2

  local lambda_function_distributable_directory
  lambda_function_distributable_directory="$(get_lambda_function_distributable_directory_path "${lambda_function_directory_relative_path}")"

  lambda_function_code_s3_key_prefix="${code_s3_key_prefix}${lambda_function_directory_relative_path}/"

  aws s3 sync \
    "${lambda_function_distributable_directory}" \
    "s3://${code_s3_bucket}/${lambda_function_code_s3_key_prefix}" > /dev/null

  echo "${lambda_function_code_s3_key_prefix}${lambda_function_code_bundle_file_name}"
}

deploy() {
  local test_doubles_macro_code_s3_key="$1"

  echo "Deploying infrastructure..." 1>&2

  aws cloudformation deploy \
    --template-file "${script_directory_path}/../template.yaml" \
    --stack-name "${stack_name}" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
      MacroNamePrefix="${macro_name_prefix}" \
      CodeS3Bucket="${code_s3_bucket}" \
      TestDoublesMacroCodeS3Key="${test_doubles_macro_code_s3_key}"
}

rm -rf "${distributable_directory_path:?}"
mkdir -p "${distributable_directory_path}"

test_doubles_macro_code_bundle_file_name="$(build_lambda_function_code_bundle "macros/test-doubles")"
test_doubles_macro_code_s3_key="$(upload_lambda_function_code_bundle "macros/test-doubles" "${test_doubles_macro_code_bundle_file_name}")"
deploy "${test_doubles_macro_code_s3_key}"