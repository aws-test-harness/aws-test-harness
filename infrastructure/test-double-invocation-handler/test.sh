#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

cleanup() {
    pkill -P $$ || true
}
trap cleanup SIGINT SIGTERM EXIT

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

function background_execute {
  local project_relative_path=$1
  local pid_variable_name=$2

  project_absolute_path="${script_directory_path}/${project_relative_path}"
  log_file="${project_absolute_path}/test.log"

  rm -f "${log_file}"

  echo "Running tests under ${project_absolute_path}..." >&2
  "${project_absolute_path}/test.sh" 1> "${log_file}" 2>&1 &
  eval "$pid_variable_name=$!"
}

function report {
  local project_relative_path=$1
  local test_execution_pid=$2

  project_absolute_path="${script_directory_path}/${project_relative_path}"
  log_file="${project_absolute_path}/test.log"

  echo ""
  echo -e "\033[33mOutput from running tests under ${project_absolute_path}:\033[0m"
  tail -F -n +1 "${log_file}" 2>&1 &
  log_tail_pid=$!
  echo ""

  set +e # don't exit script on test failure
  wait "${test_execution_pid}"
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

messaging_tests_pid=
background_execute messaging messaging_tests_pid

function_code_tests_pid=
background_execute function-code function_code_tests_pid

infrastructure_tests_pid=
background_execute infrastructure infrastructure_tests_pid

report messaging "${messaging_tests_pid}"
report function-code "${function_code_tests_pid}"
report infrastructure "${infrastructure_tests_pid}"