# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Test Harness is a Python framework for integration testing of AWS serverless applications, particularly Step Functions state machines and Lambda functions. It provides sophisticated mocking capabilities using real AWS resources as test doubles.

## Common Commands

### Setup and Development
```bash
make setup                    # Initialize dev environment with UV
uv sync                      # Sync dependencies
```

### Building
```bash
make build                   # Build all components (infrastructure, tools, library)
make build-library          # Build Python package only
make build-infrastructure   # Build CloudFormation templates and macros
```

### Testing
```bash
make test-example           # Run all example tests
uv run --directory example pytest tests                    # Run tests directly
uv run --directory example pytest tests/test_specific.py   # Run specific test file
```

**Note**: AWS_PROFILE is not needed when running tests - the tests use configured credentials from the environment.

### Deployment
```bash
make deploy-example         # Deploy example application using SAM
make deploy-infrastructure  # Deploy test harness infrastructure
```

### Fast State Machine Updates
For faster iteration when only changing state machine ASL definitions:
```bash
AWS_PROFILE=<profile> ./tools/update-state-machine.sh \
  --cfn-stack <stack-name> \
  --cfn-resource ExampleStateMachine/StateMachine \
  --definition example/example-state-machine/statemachine.asl.yaml
```
This bypasses CloudFormation deployment and directly updates the Step Functions definition.
**Note**: Stack name is available in `example/config.json` under `sandboxStackName`.

## Architecture Overview

### Core Components

**TestResourcesFactory** (`src/aws_test_harness/test_resources_factory.py`)
- Main entry point for creating test resources
- Manages test sessions and resource lifecycle

**AWSResourceMockingEngine** (`src/aws_test_harness/aws_resource_mocking_engine.py`)
- Provides mocking capabilities for AWS services
- Uses SQS queues and DynamoDB for message-based mocking

**StateMachine** (`src/aws_test_harness/state_machine.py`)
- Wrapper for AWS Step Functions with testing capabilities
- Supports execution tracking and result verification

**AWSTestDoubleDriver** (`src/aws_test_harness/aws_test_double_driver.py`)
- Manages test doubles for AWS resources (Lambda, S3, DynamoDB)
- Configures mock behavior and captures invocations

### Infrastructure Components

**CloudFormation Macros** (`infrastructure/macros/`)
- Dynamic template generation for test infrastructure
- Automatically provisions necessary AWS resources based on test requirements

**Template System** (`infrastructure/templates/`)
- `test-doubles/`: Creates mock AWS services infrastructure
- `tester-role/`: IAM roles and permissions for testing

### Testing Patterns

The framework supports several sophisticated testing patterns:

1. **Test Doubles**: Mock Lambda functions with configurable behavior
2. **State Machine Testing**: Execute and verify Step Functions workflows
3. **Message-Based Mocking**: SQS/DynamoDB-driven mock interactions
4. **Session Isolation**: Unique session IDs prevent test interference

## Project Structure

- `src/aws_test_harness/` - Core Python library
- `infrastructure/` - CloudFormation templates and macros
- `example/` - Complete working example with Lambda functions and tests
- `tools/` - Build and deployment utilities
- `scripts/` - Build automation scripts

## Development Notes

- Uses UV package manager (faster than pip/conda)
- Requires Python 3.11+
- Heavy AWS integration requiring proper AWS credentials
- CloudFormation-based infrastructure deployment
- Session-based testing with automatic cleanup
- No explicit linting/formatting configuration - follows Python standards
- **Spike Development**: This is a spike project - drive all changes by adding or extending tests in the acceptance test suite

## Testing Philosophy

This framework tests real AWS integrations using actual AWS resources configured as test doubles, rather than local mocks. Tests provision temporary AWS infrastructure, execute workflows, and verify behavior through message queues and result stores.

## Commit Guidelines

- Commit messages should not contain Claude as co-author or reference that claude was used

## Development Approach

- Work in small steps, starting from a failing test
- **NEVER write a single line of production code without a failing test first**
- **ALWAYS run the test after each change to see the actual failure**
- **DO NOT skip ahead or assume what the next failure will be**
- Implement the simplest code possible to make the test pass
- Work from the outer layers of the code downwards

## Feature Planning

- Feature plans are stored in the `features/` directory
- Each feature has its own markdown file with detailed implementation plans
- Plans are marked as ROUGH and require step-by-step confirmation before implementation
- Always check for existing feature plans before starting new work

## Deployment Notes

- To deploy the sandbox, you need to prefix the make command with an AWS_PROFILE environment variable and you need to provide a STACK_TEMPLATES_S3_BUCKET_NAME parameter. Use information from CLAUDE.local.md to determine correct values.