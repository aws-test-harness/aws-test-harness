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

Key parameters: Cluster, TaskDefinition, ContainerOverrides, LaunchType (FARGATE), NetworkConfiguration

## Proposed Architecture

### Core Components
- **Test Double ECS Tasks** - Containerized test doubles replacing real ECS tasks
- **Custom Docker Image** - Pre-built image with boto3 dependency
- **ECR Repository** - Private container registry for test harness Docker images
- **Message Flow** - Same SQS/DynamoDB pattern as existing mocks
- **ECS Infrastructure** - Cluster, task definitions, IAM roles

### Mock Registration Pattern
```python
mock_handler = mocking_engine.mock_an_ecs_task(
    'TaskDefinitionFamily', 
    lambda task_input, overrides: {'result': 'processed', 'exitCode': 0}
)
```

## Implementation Plan (Test-Driven Vertical Slices)

### Iteration 1: Minimal End-to-End ECS Task Mocking

**Goal**: Get one simple ECS task mock working end-to-end with Step Functions sync pattern

**1.1 Extend Existing Acceptance Test**
- Modify existing test in `example/tests/test_state_machine.py`
- Add ECS task as the FIRST state in the example step function (fail fast)
- Test Step Functions calling one ECS task with sync pattern (.sync)
- Test should mock an ECS task and verify it was called with expected parameters

**1.2 Minimal Infrastructure (Hardcoded Values)**
- Add basic ECS Cluster to CloudFormation template (hardcoded name)
- Add single ECS Task Definition for one task family (hardcoded family name)
- Add minimal IAM roles for ECS execution (hardcoded permissions)
- Hardcode VPC parameters initially (use existing test infrastructure VPC/subnets)

**1.3 Custom Docker Image and ECR Repository**
- Create ECR repository as part of infrastructure deployment
- Build custom Docker image with boto3 pre-installed
- Push image to ECR repository during infrastructure setup
- Update task definition to use custom image from ECR

**1.4 Minimal Mock Registration**
- Add `mock_an_ecs_task()` method to AWSResourceMockingEngine
- Create basic ECSTaskMock class with minimal functionality
- Support only sync (.sync) pattern initially

**1.5 Minimal Message Handling**
- Extend MessageListener to handle ECS task messages
- Execute mock handler and store simple result in DynamoDB
- Return success status

**1.6 Make Test Pass**
- Implement just enough functionality to make the acceptance test pass
- Focus on happy path only

### Iteration 2: Add Task Token Callback Pattern  

**Goal**: Support Step Functions task token callbacks

**2.1 Extend Test**
- Add test case for waitForTaskToken pattern in existing test
- Test that container receives and uses task token for callback

**2.2 Extend Implementation**
- Pass task token as environment variable to container
- Update S3 script to handle task token callbacks
- Implement Step Functions callback in container

### Iteration 3: Add Error Handling and Failure Scenarios

**Goal**: Support ECS task failures and error conditions

**3.1 Extend Test**
- Add test cases for ECS task failure scenarios
- Test Step Functions error handling

**3.2 Extend Implementation**
- Add ECSTaskFailure exception class
- Support non-zero exit codes
- Handle Step Functions failure states

### Iteration 4: Add Multiple Task Families

**Goal**: Support mocking different ECS task definition families

**4.1 Extend Test**
- Test multiple different task families in same test
- Verify isolation between different task mocks

**4.2 Extend Implementation**
- Update CloudFormation for dynamic task definition creation
- Extend mock registration for multiple families
- Add CloudFormation macro support if needed

### Iteration 5: Parameterize Infrastructure

**Goal**: Replace hardcoded values with proper parameters

**5.1 Update CloudFormation**
- Replace hardcoded VPC values with parameters
- Add support for user-provided subnet and security group IDs
- Make task family names configurable

**5.2 Update Documentation**
- Document required user parameters
- Add usage examples

### Iteration 6: Polish and Documentation

**Goal**: Production-ready implementation with documentation

**6.1 Comprehensive Testing**
- Add edge case tests
- Performance testing
- Security testing

**6.2 Documentation**
- Update CLAUDE.md with ECS mocking capabilities
- Add usage examples and patterns
- Document user requirements (VPC, subnets, security groups)

### Nice-to-Have (Future Iterations)

**Container Overrides Support**
- Support ECS container overrides (command, environment variables)
- Test Step Functions passing container overrides
- Lower priority - can be added later if needed

**Request Response Pattern**
- Support ECS RunTask without waiting (Request Response pattern)
- Currently not needed - sync and task token patterns are sufficient

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
- **Use AWS Fargate launch type** - Serverless containers, no EC2 management
- **Use existing VPC infrastructure** - Accept VPC parameters, don't create/manage VPCs
- **Use public subnets with assigned public IPs** - ECS tasks run in public subnets for direct internet access (no NAT Gateway needed)
- **Simple networking approach** - Zero networking costs, direct access to Docker registries and AWS services
- **Use custom Docker image with pre-installed dependencies** - Build image with boto3 dependency
- **Store image in ECR repository** - Private container registry managed as part of infrastructure
- **Minimal resource allocation** - 256 CPU / 512 MB memory for cost efficiency
- Maintain message-based async communication
- Support all Step Functions ECS integration patterns
- Preserve session isolation and parallel test execution

## Risk Considerations

- Container startup time may affect test performance
- ECS infrastructure costs during testing
- Complexity of supporting all RunTask parameter combinations
- S3 network latency for code fetching
- Need proper IAM permissions for S3 access from containers
- **Security consideration**: ECS tasks have public IPs (mitigated by proper security group rules)

## User Requirements

Users of the test harness will need to provide:
- **VPC ID**: Existing VPC where ECS tasks will run
- **Public Subnet IDs**: One or more public subnets with Internet Gateway routes
- **Security Group ID**: Security group allowing outbound HTTPS (443) access to 0.0.0.0/0

---

**Next Steps:** 
1. Review and confirm this plan
2. Begin with acceptance test creation
3. Implement incrementally with step-by-step confirmation

## Current Status - ECS Task Integration

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
- ✅ Added conditional ECS execution with Choice step for test isolation
- ✅ Tests 2-4 skip ECS task and run quickly (~40s vs 90s+)

**Current Focus**:
ECS infrastructure is working correctly. Need to implement the mocking framework integration:
1. **Implement ECS message handling** in MessageListener for task invocation events
2. **Connect mocking engine** to register ECS task handlers with message listener
3. **Test mock assertions** to verify ECS tasks are called with expected parameters

**Immediate Next Steps**:
1. **Extend ECS task exit code control** - Modify `ecs_task_runner.py` to support configurable exit codes based on mock handler return values ✅ COMPLETED
2. **Pass all environment variables to mock handler** - Make all ECS task environment variables available to the local handler function so it can conditionally behave based on Step Functions state-specific environment variable values
3. **Provide script parameters to mock handler** - Pass any command-line arguments/parameters provided to the Python script to the mock handler for additional conditional behavior control
4. **Test command override behavior** - Add test to verify that Step Functions can pass arguments via ContainerOverrides.Command and that the ECS task runner receives and processes them correctly (enabled by ENTRYPOINT change)

**Files Modified**:
- `infrastructure/macros/src/test_doubles.py` - Added ECS execution role and updated task definition
- `example/config.json` - Added VPC parameters and S3 bucket name
- `example/example-state-machine/statemachine.asl.yaml` - Added NetworkConfiguration and Choice step for conditional execution
- `Makefile` - Updated deploy-example-sandbox to use config.json values, added FORCE option
- `example/tests/test_state_machine.py` - Tests 2-4 skip ECS task for fast execution
- All templates updated to pass VPC parameters through the chain

**VPC Configuration**: Now fully parameterized via example/config.json with automatic extraction in Makefile.

**Test Status**:
- ✅ Test 1: Still in progress (ECS mocking framework integration needed)
- ✅ Tests 2-4: Pass quickly by skipping ECS task

**Open Questions**:
- **ECS Cluster Ownership**: Should library users supply their own ECS cluster ARN rather than the test harness creating one for them? Currently we auto-create a minimal Fargate cluster, but users might want to use existing clusters with specific configurations, capacity providers, or cost optimization settings. Consider adding an optional `ECSClusterArn` parameter alongside the current auto-creation approach.

- **Environment Variable Override Support**: How to support passing overridden environment variables to ECS tasks from Step Functions, whilst still relying on environment variables for events queue URL, task family, etc? This would enable tests to pass dynamic data to ECS tasks while maintaining the infrastructure-provided configuration. Potential approaches:
  - Use Step Functions ContainerOverrides.Environment to pass test-specific variables
  - Merge infrastructure env vars (EVENTS_QUEUE_URL, TASK_FAMILY) with test-provided overrides
  - Consider namespace separation (e.g., TEST_* prefix for overrideable variables)
  - Ensure infrastructure variables remain protected and cannot be overridden
  - **Note**: Command override support (via ENTRYPOINT) provides one approach, but consumers may still need env var overrides to test real-world scenarios where their Step Functions interact with ECS tasks this way

## Custom Docker Image Architecture

### ECR Repository Creation
- **ECR Repository** - Created as part of infrastructure deployment in test-doubles macro
- **Repository Name Pattern** - `aws-test-harness/ecs-task-mock` or similar standardized naming
- **Lifecycle Policy** - Auto-delete images older than 7 days to control costs
- **Access Control** - IAM permissions for ECS task execution role to pull images

### Docker Image Build Process
- **Base Image** - `python:3.11-slim` for minimal size and security
- **Pre-installed Dependencies** - boto3, urllib3, and other required packages
- **Mocking Framework Code** - Embedded Python script for message sending and session handling
- **Build Integration** - Docker build and push as part of `make deploy-infrastructure`

### Infrastructure Integration
- **Build Script** - Add Docker build to existing infrastructure deployment process
- **Image URI Reference** - Task definitions reference ECR image URI dynamically
- **Version Management** - Use deployment timestamp or commit hash as image tags

### Deployment Flow
1. **Infrastructure Deploy** - Create ECR repository first
2. **Docker Build** - Build image with latest mocking framework code
3. **Image Push** - Push to ECR repository with appropriate tag
4. **Task Definition Update** - Update ECS task definitions to use new image URI
5. **CloudFormation Deploy** - Deploy updated task definitions

## Technical Debt

- **ECS IAM PassRole Permissions**: The `iam:PassRole` permission in `example/example-state-machine/template.yaml` currently uses a wildcard resource (`"*"`). This should be restricted to only the specific execution role ARN that ECS tasks need to pass. Consider creating a specific ECS execution role in the test-doubles macro and referencing it explicitly in the permissions.