#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

cleanup() {
    pkill -P $$ || true
}
trap cleanup SIGINT SIGTERM EXIT

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

pid_variable_name_for() {
  local test_path="$1"
  echo "pid_$(echo -n "${test_path}" | sha1sum | cut -d' ' -f1)"
}

function background_execute_tests {
  local project_absolute_path=$1
  local pid_variable_name=$2

  log_file="${project_absolute_path}/test.log"
  rm -f "${log_file}"
  echo "Running tests under ${project_absolute_path}..." >&2
  "${project_absolute_path}/test.sh" 1> "${log_file}" 2>&1 &
  eval "${pid_variable_name}=$!"
}

function foreground_test_result {
  local project_absolute_path=$1
  local pid_variable_name=$2
  local pid=${!pid_variable_name}

  log_file="${project_absolute_path}/test.log"

  echo ""
  echo -e "\033[33mOutput from running tests under ${project_absolute_path}:\033[0m"
  tail -F -n +1 "${log_file}" 2>&1 &
  log_tail_pid=$!
  echo ""

  set +e # don't exit script on test failure
  wait "${pid}"
  exit_code=$?
  set -e

  sleep 1 # give tail a moment to flush
  kill "${log_tail_pid}" || true

  if [ "${exit_code}" -eq 0 ]; then
      echo -e "Tests under ${project_absolute_path} \033[32mSUCCEEDED\033[0m"
  else
      echo -e "Tests under ${project_absolute_path} \033[31mFAILED\033[0m"
  fi

  return "${exit_code}"
}

test_paths=(
    messaging
    function-code
    infrastructure
)

for test_path in "${test_paths[@]}"; do
    background_execute_tests "${script_directory_path}/${test_path}" "$(pid_variable_name_for "${test_path}")"
done

for test_path in "${test_paths[@]}"; do
    foreground_test_result "${script_directory_path}/${test_path}" "$(pid_variable_name_for "${test_path}")"
done
