#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

state_machine_definition_relative_file_path="${1}"
state_machine_arn="${2}"

script_directory_path="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

state_machine_definition_file_path="${script_directory_path}/${state_machine_definition_relative_file_path}"

if [ ! -e "${state_machine_definition_file_path}" ]; then
  echo "State machine definition file not found at ${state_machine_definition_file_path}"
  exit 1
fi

definitionTemplate="$(yq eval -P -o=json "${state_machine_definition_file_path}")"

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
definition="$(renderDefinition "${definitionTemplate}" "${definitionSubstitutions}")"
previewDefinitionChanges "${state_machine_arn}" "${definition}"
updateStateMachineDefinition "${state_machine_arn}" "${definition}"
