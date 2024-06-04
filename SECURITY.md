## GitHub Security Policy

### Reporting a Vulnerability

#### Contact Information

If you discover a security vulnerability in the API-Scripts repository, please report it to Ian Young at [ian.young@verkada.com](mailto:ian.young@verkada.com). If you prefer to keep your identity private, please use this email address for communication.

Alternatively, you may create an Issue on GitHub with the tag "vulnerability". Please ensure that no confidential or sensitive information is disclosed in the public Issue.

#### Response Time

Upon receiving a vulnerability report, Ian Young will acknowledge it as soon as possible. Please note that response times may vary, especially if Ian is traveling.

For high-severity vulnerabilities, Ian will investigate and address them on the same day. For medium to low-severity vulnerabilities, please allow up to a week for a resolution.

#### Fix and Resolution

If the fix for a vulnerability is considered stable during development, it will be directly pushed to the main branch. Otherwise, it will be pushed to the 'wip' (work in progress) branch for testing to ensure stability before deployment.

Reporters are encouraged to issue their own pull requests with fixes or propose solutions for identified vulnerabilities.

During code reviews, it is ensured that no open secrets are visible to the public, and dependency versions are checked to ensure they include the latest security patches.

#### Dependency Management

Dependabot is configured to manage all dependencies and update them automatically. Updates are checked daily to ensure the repository is up-to-date with the latest security patches.

#### Confidentiality and False Reports

Only Ian Young will have access to the original vulnerability report. If desired, the reporter's email may be masked to maintain confidentiality. No repercussions will be taken if the report is found to be false.

### Responsible Disclosure

We encourage responsible vulnerability research and disclosure. Reporters can help improve the security of the project by following these steps and responsibly reporting vulnerabilities as they are found.

For more information on how to contribute to the repository, please refer to the Development page of the Wiki: [Development Page](https://github.com/ian-young/API_Scripts/edit/main/Wiki/Development.md).
