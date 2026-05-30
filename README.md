# AgentBox SDK

Public TypeScript and Python SDKs for [AgentBox](https://agentbox.niuniu.dev/),
a private state and scoped sharing layer for AI agents.

This repository contains the public SDK source, examples, and release notes.
The hosted AgentBox service and deployment infrastructure are maintained
separately.

## Packages

| Runtime | Package | Install |
| --- | --- | --- |
| TypeScript / JavaScript | [`@niuniu-ai/agentbox`](https://www.npmjs.com/package/@niuniu-ai/agentbox) | `npm install @niuniu-ai/agentbox` |
| Python | [`niuniu-agentbox`](https://pypi.org/project/niuniu-agentbox/) | `python3 -m pip install niuniu-agentbox` |

## Quick Start

Use the public production AgentBox service for Agent Card discovery:

```text
https://agentbox.niuniu.dev
```

TypeScript:

```ts
import { discoverAgentBox } from "@niuniu-ai/agentbox";

const service = await discoverAgentBox({
  baseUrl: "https://agentbox.niuniu.dev"
});
```

Python:

```python
from agentbox import discover_agentbox

service = discover_agentbox(base_url="https://agentbox.niuniu.dev")
```

Creating production boxes requires an OIDC identity token from a provider
configured by AgentBox, such as Google. See the package READMEs for complete
examples:

- [TypeScript SDK](./packages/sdk-js/README.md)
- [Python SDK](./packages/sdk-python/README.md)
- [Cross-runtime SDK reference](./docs/sdk-reference.md)
- [SDK release runbook](./docs/sdk-release.md)

## Repository Layout

```text
packages/sdk-js/       TypeScript SDK package
packages/sdk-python/   Python SDK package
docs/                  Public SDK usage and API reference
```

## Development

Install JavaScript dependencies:

```bash
npm install
```

Run TypeScript checks:

```bash
npm run typecheck
npm run release:check:sdk-js
```

Run Python checks:

```bash
python3 -m unittest discover packages/sdk-python/tests
python3 -m pip wheel packages/sdk-python --no-deps --wheel-dir /tmp/niuniu-agentbox-python-wheel
```

## Support

Use GitHub issues for SDK bugs, install problems, and documentation confusion.
Please do not open public issues for security reports; see
[SECURITY.md](./SECURITY.md).

## Releases

SDK versions are published from this repository after npm and PyPI trusted
publishers are configured for `niuniu-dev-ai/agentbox-sdk`. GitHub releases use
tags such as `v0.1.7` and match the npm/PyPI package versions.

## License

MIT
