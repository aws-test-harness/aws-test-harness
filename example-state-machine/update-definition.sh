#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

force=false

usage() {
  echo "Usage: $0 [--help] [--arn arn] [--definition path] [--force]"
  exit 1
}

while [[ "${1:-}" != "" ]]; do
    case ${1} in
        --help )
            usage
            ;;
        --cfn-stack )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --cfn-stack"
              usage
            fi

            stack_name="${1}"
            ;;
        --cfn-resource )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --cfn-resource"
              usage
            fi

            resource_logical_id="${1}"
            ;;
        --arn )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --arn"
              usage
            fi

            state_machine_arn="${1}"
            ;;
        --definition )
            shift

            if [ -z "${1:-}" ]; then
              echo "Missing argument for --definition"
              usage
            fi

            # TODO: Derive the state machine ARN from the (nested) stack logical resource ID
            state_machine_definition_relative_file_path="${1}"
            ;;
        --force )
            force=true
            ;;
        * )
            echo "Unknown option: ${1}"
            usage
            ;;
    esac
    shift
done

function get_cfn_resource_physical_id {
  local stack_name="$1"
  local resource_logical_id="$2"

  if [[ "${resource_logical_id}" == */* ]]; then
    local nested_stack_logical_id
    local nested_resource_logical_id

    nested_stack_logical_id=$(echo "$resource_logical_id" | cut -d'/' -f1)
    nested_stack_name="$(get_cfn_resource_physical_id "${stack_name}" "${nested_stack_logical_id}")"

    nested_resource_logical_id=$(echo "$resource_logical_id" | cut -d'/' -f2)

    get_cfn_resource_physical_id "${nested_stack_name}" "${nested_resource_logical_id}"
    return
  fi

  aws cloudformation describe-stack-resource \
    --stack-name "${stack_name}" \
    --logical-resource-id "${resource_logical_id}" | \
    jq -r '.StackResourceDetail.PhysicalResourceId'
}

if [ -n "${stack_name:-}" ] || [ -n "${resource_logical_id:-}" ]; then
  if [ -z "${stack_name:-}" ] || [ -z "${resource_logical_id:-}" ]; then
    echo "Both --cfn-stack and --cfn-resource must be provided"
    usage
  fi

  # TODO: Cache result in local file
  state_machine_arn="$(get_cfn_resource_physical_id "${stack_name}" "${resource_logical_id}")"
fi

script_directory_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

state_machine_definition_file_path="${script_directory_path}/${state_machine_definition_relative_file_path}"

if [ ! -e "${state_machine_definition_file_path}" ]; then
  echo "State machine definition file not found at ${state_machine_definition_file_path}"
  exit 1
fi

function getDefinitionSubstitutions {
  local state_machine_arn="$1"

  aws stepfunctions list-tags-for-resource \
    --resource-arn "${state_machine_arn}" | \
    jq '[.tags[]|select(.key | startswith("DefinitionSubstitutions:"))] | map({(.key | gsub("^DefinitionSubstitutions:"; "")): .value}) | add'
}

function renderDefinition {
  local definitionTemplate="$1"
  local definitionSubstitutions="$2"

  for key in $(echo "${definitionSubstitutions}" | jq -r 'keys[]'); do
    value=$(echo "${definitionSubstitutions}" | jq -r --arg k "$key" '.[$k]')
    definitionTemplate="${definitionTemplate//\$\{$key\}/$value}"
  done

  echo "${definitionTemplate}"
}

function previewDefinitionChanges {
  local state_machine_arn="$1"
  local updatedDefinition="$2"

  state_machine_description="$(aws stepfunctions describe-state-machine \
    --state-machine-arn "${state_machine_arn}")"

  currentDefinition="$(echo "${state_machine_description}" | jq '.definition | fromjson')"

  diffOutput="$(diff -C 5 <(echo "${currentDefinition}") <(echo "${updatedDefinition}") || true)"

  if [ -z "${diffOutput}" ]; then
    echo "No changes would be made to the state machine definition. Exiting."
    exit 0
  else
    echo "The following changes would be made to the state machine definition:"
    echo "${diffOutput}"

    read -r -p "Are you sure you want to proceed? (y/n) " answer
    if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
        echo "Aborting."
        exit 0
    fi
  fi
}

function updateStateMachineDefinition {
  local state_machine_arn="$1"
  local definition="$2"

  aws stepfunctions update-state-machine \
    --state-machine-arn "${state_machine_arn}" \
    --definition "${definition}" > /dev/null

  echo "State machine definition updated at $(date +"%H:%M:%S on %Y-%m-%d")"
}

definitionSubstitutions="$(getDefinitionSubstitutions "${state_machine_arn}")"
definitionTemplate="$(yq eval -P -o=json "${state_machine_definition_file_path}")"
definition="$(renderDefinition "${definitionTemplate}" "${definitionSubstitutions}")"

if [ "${force}" != true ]; then
  previewDefinitionChanges "${state_machine_arn}" "${definition}"
fi

updateStateMachineDefinition "${state_machine_arn}" "${definition}"
