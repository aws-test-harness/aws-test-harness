#!/usr/bin/env bash

set -o nounset -o errexit -o pipefail

cleanup() {
    pkill -P $$ || true
}
trap cleanup SIGINT SIGTERM EXIT

script_directory_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

function background_execute {
  local test_type=$1
  local pid_variable_name=$2

  rm "${script_directory_path}/tests/${test_type}.log" || true

  echo "Running ${test_type} tests..." >&2
  uv run --isolated --directory "${script_directory_path}" pytest --color=yes "${script_directory_path}/tests/aws_test_harness_tests/${test_type}" 1> "${script_directory_path}/tests/${test_type}.log" 2>&1 &
  eval "$pid_variable_name=$!"
}

function report {
  local test_type=$1
  local test_execution_pid=$2

  echo ""
  echo -e "\033[33mOutput from ${test_type} tests:\033[0m"
  tail -F -n +1 "${script_directory_path}/tests/${test_type}.log" 2>&1 &
  log_tail_pid=$!
  echo ""

  set +e # don't exit script on test failure
  wait "${test_execution_pid}"
  exit_code=$?
  set -e

  sleep 1 # give tail a moment to flush
  kill "${log_tail_pid}" || true

  if [ "${exit_code}" -eq 0 ]; then
      echo -e "Result for ${test_type} tests: \033[32mSUCCEEDED\033[0m"
  else
      echo -e "Result for ${test_type} tests: \033[31mFAILED\033[0m"
  fi

  return "${exit_code}"
}

unit_tests_pid=
background_execute unit unit_tests_pid

integration_tests_pid=
background_execute integration integration_tests_pid

acceptance_tests_pid=
background_execute acceptance acceptance_tests_pid

report unit "${unit_tests_pid}"
report integration "${integration_tests_pid}"
report acceptance "${acceptance_tests_pid}"