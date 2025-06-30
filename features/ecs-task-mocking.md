# ECS Task Mocking Feature Plan

**Status:** ROUGH PLAN - Requires step-by-step confirmation before implementation

**Objective:** Add ECS task mocking capability to AWS Test Harness, similar to existing Lambda and Step Function mocking.

## Research Summary

### Current Architecture Understanding
- Test Double Pattern using real AWS infrastructure
- Message-based communication via SQS + DynamoDB
- Session isolation with unique session IDs
- CloudFormation-based infrastructure deployment

### ECS Integration Points
Step Functions supports three ECS RunTask patterns:
1. **Request Response** - Simple RunTask without waiting
2. **Run a Job (.sync)** - Synchronous execution waiting for completion
3. **Wait for Task Token** - Callback pattern with task token

Key parameters: Cluster, TaskDefinition, ContainerOverrides, LaunchType, NetworkConfiguration

## Proposed Architecture

### Core Components
- **Test Double ECS Tasks** - Containerized test doubles replacing real ECS tasks
- **Lightweight Container** - Use public `python:3.11-slim` image with S3 code fetching
- **Message Flow** - Same SQS/DynamoDB pattern as existing mocks
- **ECS Infrastructure** - Cluster, task definitions, IAM roles

### Mock Registration Pattern
```python
mock_handler = mocking_engine.mock_an_ecs_task(
    'TaskDefinitionFamily', 
    lambda task_input, overrides: {'result': 'processed', 'exitCode': 0}
)
```

## Implementation Plan

### Phase 1: Core ECS Mocking Infrastructure

**1.1 CloudFormation Template Updates** (`infrastructure/templates/test-doubles/template.yaml`)
- Add ECS Cluster resource
- Add ECS Task Definition template with parameterized container image
- Add ECS Service definitions for test doubles
- Add IAM roles for ECS task execution and Step Functions integration

**1.2 ECS Task Definition Configuration**
- Use lightweight public image: `python:3.11-slim`
- Configure task to fetch Python code from S3 at runtime
- Container command: `python -c "import urllib.request; exec(urllib.request.urlopen('s3://bucket/path/ecs_test_double.py').read())"`
- Python code in S3 follows Lambda test double pattern:
  - Retrieve session ID from S3 TestContextBucket
  - Send task invocation message to SQS EventsQueue
  - Poll DynamoDB ResultsTable for mock handler response
  - Exit with appropriate code based on mock result

**1.3 Update AWSTestDoubleDriver** (`src/aws_test_harness/aws_test_double_driver.py`)
- Add methods for accessing ECS test double resources:
  - `ecs_cluster()` - returns ECS cluster reference
  - `ecs_task_definition(family)` - returns task definition ARN
  - `ecs_tasks()` - returns list of available ECS task mocks

### Phase 2: ECS Mock Registration and Management

**2.1 Update AWSResourceMockingEngine** (`src/aws_test_harness/aws_resource_mocking_engine.py`)
- Add `mock_an_ecs_task(task_family, handler)` method
- Create ECSTaskMock class similar to existing mock classes
- Handle ECS-specific parameters (cluster, task definition, overrides)
- Support different integration patterns (sync, async, task token)

**2.2 Update MessageListener** (`src/aws_test_harness/message_listener.py`)
- Add ECS task message handling alongside Lambda and Step Function messages
- Process ECS task invocation messages with task parameters
- Execute registered ECS mock handlers
- Store results with task completion status (STOPPED, exit code)

**2.3 ECS Task Mock Classes**
- **ECSTaskMock**: Main mock object with assertion capabilities
- **ECSTaskExecution**: Represents task execution with status tracking
- **ECSTaskFailure**: Exception class for simulating task failures

### Phase 3: Integration with Step Functions

**3.1 Step Function ECS Integration Support**
- Handle different RunTask integration patterns:
  - Request Response: Immediate return with task ARN
  - Sync (.sync): Wait for task completion before proceeding
  - Task Token: Pass token to container for callback

**3.2 CloudFormation Macro Updates** (`infrastructure/macros/`)
- Extend existing macros to support ECS task parameter processing
- Dynamic creation of ECS resources based on test requirements

### Phase 4: Testing and Examples

**4.1 Acceptance Tests** (following the spike development approach)
- Create acceptance tests in example directory
- Test all three ECS integration patterns
- Test container overrides and environment variables
- Test failure scenarios and error handling

**4.2 Example State Machine** (`example/`)
- Add example Step Function that calls ECS tasks
- Demonstrate different RunTask patterns
- Show mock configuration and assertions

**4.3 Documentation Updates**
- Update CLAUDE.md with ECS mocking capabilities
- Add usage examples and patterns

## Implementation Order (Test-Driven)

**⚠️ IMPORTANT: Each step requires confirmation before proceeding**

1. **Start with failing acceptance test** - Create test that tries to mock an ECS task
2. **Implement minimal CloudFormation infrastructure** - Just enough to deploy ECS cluster
3. **Create S3-based test double script** - Python script that containers fetch and execute
4. **Add ECS mock registration to AWSResourceMockingEngine** - Minimal implementation
5. **Implement message handling for ECS tasks** - Extend MessageListener
6. **Add sync pattern support** - Most common use case first
7. **Add async and task token patterns** - Extended functionality
8. **Add comprehensive error handling and assertions** - Production-ready features

## Key Design Decisions

- Follow existing test double patterns for consistency
- Use containerized approach for ECS task simulation
- **Use lightweight public Python image** - Avoid custom Docker builds
- **Fetch test double code from S3 at runtime** - Dynamic code execution
- Maintain message-based async communication
- Support all Step Functions ECS integration patterns
- Preserve session isolation and parallel test execution

## Risk Considerations

- Container startup time may affect test performance
- ECS infrastructure costs during testing
- Complexity of supporting all RunTask parameter combinations
- S3 network latency for code fetching
- Need proper IAM permissions for S3 access from containers

---

**Next Steps:** 
1. Review and confirm this plan
2. Begin with acceptance test creation
3. Implement incrementally with step-by-step confirmation