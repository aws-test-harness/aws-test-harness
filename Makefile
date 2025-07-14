VERSION := 0.0.1a22
STACK_TEMPLATES_DIRECTORY := infrastructure/templates
STACK_TEMPLATE_BUILD_TARGETS := $(shell find $(STACK_TEMPLATES_DIRECTORY) -type d -depth 1 -exec basename {} \; | sed 's/^/build-/' | sed 's/$$/-stack-template/')
FORCE?=false

.PHONY: default
default: setup

.PHONY: setup
setup:
	uv venv --seed
	uv sync
	uv venv --seed --project example
	uv sync --project example

.PHONY: clean
clean:
	rm -rf dist

.PHONY: build
build: clean build-infrastructure build-tools build-library

.PHONY: build-tools
build-tools:
	tar -czf dist/tools.tar.gz tools

.PHONY: build-infrastructure
build-infrastructure: build-stack-templates build-macros-template copy-installation-script copy-ecs-task-test-double
	tar -czf dist/infrastructure.tar.gz -C dist infrastructure && rm -rf dist/infrastructure

.PHONY: create-infrastructure-dist-directory
create-infrastructure-dist-directory:
	mkdir -p dist/infrastructure

.PHONY: build-macros-template
build-macros-template: create-infrastructure-dist-directory
	scripts/build-template.sh infrastructure/macros/template.yaml dist/infrastructure/macros.yaml

.PHONY: build-stack-templates
build-stack-templates: $(STACK_TEMPLATE_BUILD_TARGETS)

.PHONY: build-%-stack-template
build-%-stack-template: create-templates-dist-directory
	scripts/build-template.sh infrastructure/templates/$*/template.yaml dist/infrastructure/templates/$*.yaml

.PHONY: create-templates-dist-directory
create-templates-dist-directory:
	mkdir -p dist/infrastructure/templates

.PHONY: copy-installation-script
copy-installation-script: create-infrastructure-dist-directory
	cp infrastructure/scripts/install.sh dist/infrastructure

.PHONY: copy-ecs-task-test-double
copy-ecs-task-test-double: create-infrastructure-dist-directory
	cp -r infrastructure/ecs-task-test-double dist/infrastructure/

.PHONY: build-library
build-library:
	uv build -o dist/library

.PHONY: publish-non-library-assets
publish-non-library-assets:
	gh release create --prerelease --target spike --generate-notes "$(VERSION)" dist/*.tar.gz

.PHONY: publish-library
publish-library:
	uv publish --token "$(PYPI_TOKEN)" dist/library/*

.PHONY: deploy-infrastructure
deploy-infrastructure: build-infrastructure
	tar -xf dist/infrastructure.tar.gz -C dist
	AWS_PROFILE=$$(jq -r '.awsDeploymentProfile' example/config.json) ./dist/infrastructure/install.sh \
		--macros-stack-name aws-test-harness-macros \
		--stack-templates-s3-uri s3://$$(jq -r '.stackTemplatesS3BucketName' example/config.json)/aws-test-harness-templates \
		--aws-region $$(jq -r '.awsRegion' example/config.json) \
		--macro-names-prefix MacroNamesPrefix-

.PHONY: deploy-example
deploy-example:
	sam deploy \
		--profile $$(jq -r '.awsDeploymentProfile' example/config.json) \
		--template example/template.yaml \
		--config-file samconfig.toml

.PHONY: deploy-example-sandbox
deploy-example-sandbox:
	sam deploy \
		--profile $$(jq -r '.awsDeploymentProfile' example/config.json) \
		--template example/tests/sandbox/template.yaml \
		--config-file samconfig.toml \
		--parameter-overrides \
			StackTemplatesS3BucketName=$$(jq -r '.stackTemplatesS3BucketName' example/config.json) \
			VpcId=$$(jq -r '.vpcId' example/config.json) \
			SubnetIds=$$(jq -r '.subnetIds | join(",")' example/config.json) \
			SecurityGroupIds=$$(jq -r '.securityGroupIds | join(",")' example/config.json)

.PHONY: update-sandbox-state-machine
update-sandbox-state-machine:
	AWS_PROFILE=$$(jq -r '.awsDeploymentProfile' example/config.json) ./tools/update-state-machine.sh \
		--cfn-stack $$(jq -r '.sandboxStackName' example/config.json) \
		--cfn-resource ExampleStateMachine/StateMachine \
		--definition example/example-state-machine/statemachine.asl.yaml \
		$$([ "$(FORCE)" = "true" ] && echo '--force')

.PHONY: test-example
test-example:
	uv run --directory example pytest tests