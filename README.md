# AWS Test Harness

## Development

### Prerequisites
- [uv](https://docs.astral.sh/uv/)

### Development environment
Always run `./go.sh` after pulling the latest changes.

### Running tests
Create a config file at `tests/config.json` with the following content (appropriately substituted):
```json
{
  "awsProfile": "<your AWS CLI profile>",
  "cfnStackName": "<chosen name for the acceptance test stack>"
}
```

Then run `./test.sh`.