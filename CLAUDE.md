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
make deploy-example-sandbox # Deploy test sandbox with config from example/config.json
```

### AWS Resource Inspection
```bash
# Get nested stack ARN from parent stack
aws cloudformation describe-stack-resources --stack-name <parent-stack> --query "StackResources[?LogicalResourceId=='<logical-id>'].PhysicalResourceId" --output text

# Get specific resource ARNs from nested stack
aws cloudformation describe-stack-resources --stack-name <nested-stack-arn> --query "StackResources[?ResourceType=='<aws-resource-type>'].PhysicalResourceId"

# Inspect Step Functions execution history
aws stepfunctions get-execution-history --execution-arn <execution-arn> --max-results 10

# Check ECS task status
aws ecs describe-tasks --cluster <cluster-name> --tasks <task-arn>
```

### Fast State Machine Updates
For faster iteration when only changing state machine ASL definitions:
```bash
make update-sandbox-state-machine           # Review changes and confirm
make update-sandbox-state-machine FORCE=true # Skip confirmation
```
This bypasses CloudFormation deployment and directly updates the Step Functions definition.
Uses deployment profile and stack name from `example/config.json`.

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

## Testing Philosophy

This framework tests real AWS integrations using actual AWS resources configured as test doubles, rather than local mocks. Tests provision temporary AWS infrastructure, execute workflows, and verify behavior through message queues and result stores.

## Custom Commands

- **`/learn`** - Capture technical insights and update project memory before committing
- **`/wow`** - Capture ways of working insights and development process improvements

## Commit Guidelines

- **Make small, frequent commits** - Commit each meaningful change separately rather than batching multiple changes
- **Run `/learn` before committing** - Execute the custom Claude learn command to capture technical insights, then commit both the changes and updated project memory together
- **Show commit details before pushing** - After each commit, show the commit message and files changed, then ask for approval before pushing
- **Never include Claude co-author information** - Commit messages should not contain Claude as co-author or reference that Claude was used
- **Always use AWS profiles** - Never rely on default AWS credentials; always specify AWS_PROFILE for all AWS CLI commands
- **CRITICAL**: Never include sensitive information in commits, including:
  - AWS resource names (bucket names, VPC IDs, subnet IDs, etc.)
  - Account IDs, ARNs, or region-specific identifiers
  - Profile names or any deployment-specific configuration
  - Use placeholders like `<bucket-name>`, `<vpc-id>`, etc. in documentation
  - Always review diffs carefully before committing to catch sensitive data

## Development Approach

- **Spike Development**: This is a spike project - drive all changes by adding or extending tests in the acceptance test suite
- Work in small steps, starting from a failing test
- **NEVER write a single line of production code without a failing test first**
- **ALWAYS run the test after each change to see the actual failure**
- **DO NOT skip ahead or assume what the next failure will be**
- **Make ONLY the absolute minimum change required to get the test passing**
- **Do NOT add additional concerns, infrastructure, or complexity beyond what's needed for the current failure**
- **Don't implement methods until the test fails because they're missing** - Let the test drive exactly what needs to be implemented, rather than anticipating and building ahead of the actual failure
- **Strict test-driven implementation discipline** - Only implement exactly what the current test failure demands, never anticipate future needs. This prevents over-engineering, ensures solving actual problems, maintains minimal focused code, preserves TDD discipline, prevents wasted effort, and drives better API design. Use this always during TDD, especially when tempted to "get ahead" of the current failure.
- **Add additional features/infrastructure later when tests require them**
- Implement the simplest code possible to make the test pass
- **Work outside-in from failing test through execution layers** - Start with the failing test and trace down through each layer of the execution path one step at a time
- **Write calling code first, even if called methods don't exist** - When implementing integration between components, write the code that calls the method you wish existed first, let it fail with AttributeError, then implement the missing method. This drives proper API design from the caller's perspective.
- **Explain rationale before making changes** - Before implementing any change, clearly articulate why this specific change will advance the test beyond its current failure state
- **Commit and capture learnings before proceeding to next development phase** - Document new ways of working and technical insights before implementing new features
- **Always show commit details before pushing** - Display commit message and list of files changed, ask for approval before pushing to remote

### Debugging and Problem Solving
- **When deployments fail, read CloudWatch logs instead of guessing** - especially for Lambda functions and macros
- **Use CloudFormation stack events to debug nested stack failures** - check both parent and child stack events
- **Follow existing architectural patterns** - use macros where other resources use macros, not CloudFormation ForEach
- **Use fast iteration tools** - like `tools/update-state-machine.sh` for ASL changes instead of full deployments
- **Use CloudFormation stacks to find AWS resources** - Always use `aws cloudformation describe-stack-resources` to get resource ARNs before inspecting AWS services directly
- **Inspect actual AWS service state for diagnosis** - Use ECS `describe-tasks`, Step Functions `get-execution-history`, etc. to understand what really happened vs assumptions
- **Check Step Functions execution history** - Shows exact task progression, timing, and failure details with full AWS API responses
- **Default capacity provider strategy is critical for ECS** - Must set `DefaultCapacityProviderStrategy` on cluster, not just `CapacityProviders`, to avoid "No Container Instances" errors
- **ECS Task timeouts don't stop underlying containers** - Step Functions `TimeoutSeconds` fails executions but doesn't terminate ECS tasks; use task-level timeouts instead
- **CloudWatch logging requires explicit configuration** - ECS tasks need `LogConfiguration` with specific log group patterns and IAM permissions for CloudWatch access
- **Test timeout analysis requires end-to-end investigation** - When tests timeout, investigate the entire execution flow: Step Functions execution history, Lambda logs, SQS queues, and DynamoDB tables to identify where the workflow is hanging
- **Lambda mocking requires sufficient test timeout** - Lambda functions polling DynamoDB for mock results need adequate time; test timeouts should account for Step Functions orchestration overhead plus Lambda execution time
- **Verify existing functionality after changes** - When modifying shared infrastructure (like state machine logic), immediately test that existing functionality still works as expected, especially performance characteristics like test execution times

### Security
- **AWS Security**: Always maintain least privilege principles when configuring AWS resource access and IAM permissions

### Naming and Standards
- **Follow PascalCase for resource names** - consistent with existing resources like "InputTransformer", "Doubler"
- **CloudFormation logical resource IDs must be alphanumeric** - no hyphens or special characters
- **Parameter types matter** - CommaDelimitedList parameters arrive as arrays, not strings needing splitting

## Feature Planning

- Feature plans are stored in the `features/` directory
- Each feature has its own markdown file with detailed implementation plans
- Plans are marked as ROUGH and require step-by-step confirmation before implementation
- Always check for existing feature plans before starting new work

## Current Work

Current development work is documented in feature-specific files under the `features/` directory. Check `features/ecs-task-mocking.md` for the latest ECS task integration status and next steps.