# WOW Command (Way of Working)

## Description
Captures and documents ways of working insights and development process improvements discovered during the current session.

## Usage
```
/wow
```

## What it captures
- Test-driven development discipline and practices
- Development workflow improvements
- Process optimization techniques
- Problem-solving methodologies
- Code review and quality assurance approaches
- Team collaboration patterns
- Project management insights
- Communication and feedback loops
- Debugging and troubleshooting approaches
- Planning and estimation techniques

## What it excludes
- Personal or privileged information
- Secrets, credentials, or sensitive data
- User-specific details or private information
- Temporary debugging outputs
- Specific error messages containing sensitive paths
- Technical implementation details (use `/learn` for those)

## Implementation
The command reflects on the way of working technique that was just used, explains:
1. The essence of the technique
2. The value it provides
3. When it should be used

After user confirmation, it updates the relevant sections of CLAUDE.md, particularly:
- Development Approach
- Debugging and Problem Solving
- Commit Guidelines
- Custom Commands
- Ways of working principles

## Example Usage
When you notice a valuable development process insight (like "write calling code first" or "strict TDD discipline"), use `/wow` to capture and formalize that way of working for future reference.