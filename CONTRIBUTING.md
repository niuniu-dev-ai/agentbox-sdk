# Contributing

Thanks for helping improve the AgentBox SDKs.

This public repository is intentionally small. It accepts issues and pull
requests for SDK bugs, package installation problems, examples, and public SDK
documentation. The hosted AgentBox service and deployment infrastructure are
maintained separately.

## Good First Contributions

- clarify setup or auth documentation;
- add small SDK usage examples;
- fix cross-runtime SDK behavior that is covered by tests;
- improve packaging metadata or type hints.

## Pull Requests

Before opening a pull request:

1. Keep the change focused.
2. Add or update tests when SDK behavior changes.
3. Run the relevant checks:

```bash
npm run typecheck
npm run release:check:sdk-js
npm run test:sdk-python
npm run release:check:sdk-python
```

External pull requests are welcome, but acceptance depends on project fit,
maintainer capacity, and compatibility with the hosted service.

## Security

Please do not report security issues in public issues or pull requests. See
[SECURITY.md](./SECURITY.md).
