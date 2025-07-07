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
- **AWS Security**: Always maintain least privilege principles when configuring AWS resource access and IAM permissions

## Technical Debt

- **ECS IAM PassRole Permissions**: The `iam:PassRole` permission in `example/example-state-machine/template.yaml` currently uses a wildcard resource (`"*"`). This should be restricted to only the specific execution role ARN that ECS tasks need to pass. Consider creating a specific ECS execution role in the test-doubles macro and referencing it explicitly in the permissions.

## ECS Integration Patterns

**Key Implementation Insights:**
- **ECS Execution Role Required**: Fargate tasks must have `ExecutionRoleArn` with `AmazonECSTaskExecutionRolePolicy` managed policy
- **Default Capacity Provider Strategy Essential**: Must set `DefaultCapacityProviderStrategy` on cluster, not just `CapacityProviders` 
- **Lightweight Base Images**: Use `python:3.11-slim` instead of Lambda images for containerized tasks
- **VPC Configuration**: ECS tasks in `awsvpc` mode require NetworkConfiguration with subnets and security groups
- **Public IP Assignment Critical**: Must set `AssignPublicIp: ENABLED` for Docker image pulls from public registries
- **Container Commands**: Tasks need explicit commands since most base images don't have default entrypoints
- **Structured Output**: Container stdout should output JSON for Step Functions integration
- **Step Functions Data Flow**: Use `ResultPath` to preserve original input when ECS task output becomes state output

**ECS Task Definition Pattern:**
```python
# Minimal Fargate-compatible task definition
{
    'Type': 'AWS::ECS::TaskDefinition',
    'Properties': {
        'RequiresCompatibilities': ['FARGATE'],
        'NetworkMode': 'awsvpc',
        'Cpu': '256',
        'Memory': '512', 
        'ExecutionRoleArn': {'Fn::GetAtt': ['ECSTaskExecutionRole', 'Arn']},
        'ContainerDefinitions': [{
            'Name': task_family,
            'Image': 'python:3.11-slim',
            'Essential': True,
            'Command': ['python', '-c', 'import json; print(json.dumps({"status": "success"}))']
        }]
    }
}
```

**ECS Cluster Pattern:**
```python
# Cluster with default Fargate capacity provider
{
    'Type': 'AWS::ECS::Cluster',
    'Properties': {
        'CapacityProviders': ['FARGATE'],
        'DefaultCapacityProviderStrategy': [{
            'CapacityProvider': 'FARGATE',
            'Weight': 1
        }]
    }
}
```

## Testing Philosophy

This framework tests real AWS integrations using actual AWS resources configured as test doubles, rather than local mocks. Tests provision temporary AWS infrastructure, execute workflows, and verify behavior through message queues and result stores.

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

- Work in small steps, starting from a failing test
- **NEVER write a single line of production code without a failing test first**
- **ALWAYS run the test after each change to see the actual failure**
- **DO NOT skip ahead or assume what the next failure will be**
- **Make ONLY the absolute minimum change required to get the test passing**
- **Do NOT add additional concerns, infrastructure, or complexity beyond what's needed for the current failure**
- **Add additional features/infrastructure later when tests require them**
- Implement the simplest code possible to make the test pass
- Work from the outer layers of the code downwards
- **Commit and capture learnings before proceeding to next development phase** - Document new ways of working and technical insights before implementing new features

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

### Naming and Standards
- **Follow PascalCase for resource names** - consistent with existing resources like "InputTransformer", "Doubler"
- **CloudFormation logical resource IDs must be alphanumeric** - no hyphens or special characters
- **Parameter types matter** - CommaDelimitedList parameters arrive as arrays, not strings needing splitting

## Feature Planning

- Feature plans are stored in the `features/` directory
- Each feature has its own markdown file with detailed implementation plans
- Plans are marked as ROUGH and require step-by-step confirmation before implementation
- Always check for existing feature plans before starting new work

## Deployment Notes

- To deploy the sandbox, you need to prefix the make command with an AWS_PROFILE environment variable and you need to provide a STACK_TEMPLATES_S3_BUCKET_NAME parameter. Use information from CLAUDE.local.md to determine correct values.

## Current Work - ECS Task Integration

**Status**: ECS infrastructure working, implementing mocking framework

**Recent Progress**:
- ✅ Added ECS task mocking support to test-doubles macro
- ✅ Implemented VPC parameterization with config.json integration  
- ✅ Updated Makefile to extract all deployment config from example/config.json
- ✅ Added NetworkConfiguration for ECS tasks in ASL
- ✅ Deployed ECS execution role and fixed Fargate capacity provider strategy
- ✅ Fixed task definition to use python:3.11-slim with JSON output command
- ✅ Validated CloudFormation-based AWS resource inspection approach
- ✅ Fixed ECS networking with AssignPublicIp: ENABLED for Docker image pulls
- ✅ Fixed Step Functions data flow with ResultPath to preserve original input
- ✅ ECS tasks now start, execute, and complete successfully

**Current Focus**:
ECS infrastructure is working correctly. Need to implement the mocking framework integration:
1. **Implement ECS message handling** in MessageListener for task invocation events
2. **Connect mocking engine** to register ECS task handlers with message listener
3. **Test mock assertions** to verify ECS tasks are called with expected parameters

**Immediate Next Steps**:
1. **Add ECS message handling** to MessageListener class
2. **Enable ECS mock registration** in AWSResourceMockingEngine (uncomment TODO)
3. **Test ECS mocking** to verify mock.assert_called_once() works correctly

**Technical Issue**: 
ECS Fargate tasks were failing with "No Container Instances were found in your cluster" because they need an execution role. Added `ECSTaskExecutionRole` to the macro in test_doubles.py but haven't deployed it yet.

**Files Modified**:
- `infrastructure/macros/src/test_doubles.py` - Added ECS execution role and updated task definition
- `example/config.json` - Added VPC parameters and S3 bucket name
- `example/example-state-machine/statemachine.asl.yaml` - Added NetworkConfiguration  
- `Makefile` - Updated deploy-example-sandbox to use config.json values
- All templates updated to pass VPC parameters through the chain

**VPC Configuration**: Now fully parameterized via example/config.json with automatic extraction in Makefile.

**Open Questions**:
- **ECS Cluster Ownership**: Should library users supply their own ECS cluster ARN rather than the test harness creating one for them? Currently we auto-create a minimal Fargate cluster, but users might want to use existing clusters with specific configurations, capacity providers, or cost optimization settings. Consider adding an optional `ECSClusterArn` parameter alongside the current auto-creation approach.