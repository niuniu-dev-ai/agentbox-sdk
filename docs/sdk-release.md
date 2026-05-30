# SDK Release Runbook

This repository is the canonical source and publishing home for the public
AgentBox SDK packages.

## Packages

- npm: `@niuniu-ai/agentbox`
- PyPI: `niuniu-agentbox`

Trusted publishing should be configured for both packages with:

```text
GitHub owner:      niuniu-dev-ai
Repository:        agentbox-sdk
Workflow filename: publish-sdk.yml
Environment:       release
```

The npm trusted-publisher configuration can be managed from npm package
settings, or with npm CLI versions that support `npm trust`:

```bash
npm trust github @niuniu-ai/agentbox \
  --repo niuniu-dev-ai/agentbox-sdk \
  --file publish-sdk.yml \
  --env release \
  --allow-publish
```

The PyPI trusted-publisher configuration is managed from the
`niuniu-agentbox` project Publishing settings.

## Preflight

Before opening a release PR:

```bash
npm run typecheck
npm run release:check:sdk-js
npm run test:sdk-python
npm run release:check:sdk-python
```

Confirm the target version does not already exist:

```bash
npm view @niuniu-ai/agentbox@<version> version --prefer-online
python3 -m pip index versions niuniu-agentbox
```

## Publishing

Publish only after:

- the release PR is merged to `main`;
- npm and PyPI trusted publishers point at this repository;
- package dry-runs show the expected JavaScript tarball and Python wheel.

Dispatch the workflow from `main`:

```bash
gh workflow run publish-sdk.yml \
  --repo niuniu-dev-ai/agentbox-sdk \
  --ref main \
  -f publish_js=true \
  -f publish_python=true
```

Watch the workflow:

```bash
gh run list --repo niuniu-dev-ai/agentbox-sdk --workflow publish-sdk.yml --branch main --limit 5
gh run view --repo niuniu-dev-ai/agentbox-sdk <run-id> --json status,conclusion,url,jobs
```

After publishing:

1. Verify npm and PyPI show the new version.
2. Install both packages in clean temporary projects.
3. Run discovery and non-mutating health checks against
   `https://agentbox.niuniu.dev`.
4. Create a GitHub release named `v<version>` in this repository.
