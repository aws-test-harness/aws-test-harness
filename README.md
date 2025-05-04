# AWS Test Harness

## Development

### Prerequisites
- [uv](https://docs.astral.sh/uv/)
- [jq](https://jqlang.org/)
- [AWS CLI](https://aws.amazon.com/cli/)
- An AWS account

### After pulling code
Always run `./go.sh` after pulling the latest changes, to ensure your local development environment is up to date.

### Running tests
Create a config file at `tests/config.json` and another at `languages/python/tests/config.json` with the following content (appropriately substituted):
```json
{
  "awsProfile": "<your AWS CLI profile>",
  "awsRegion": "<target AWS region>",
  "cfnStackNamePrefix": "<prefix for stack names>",
}
```

Then run `./test.sh`.

### Linting
Run `./lint.sh`.

### Before pushing code
Run `./check.sh`.