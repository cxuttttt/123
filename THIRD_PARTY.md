# Upstream components

PocketAgent is a portable distribution, not an independent agent implementation.
Versions, original download URLs and SHA256 digests are pinned in upstream.lock.json.

| Component | Reused capability | License / source |
| --- | --- | --- |
| OpenCode | Agent loop, terminal UI, model providers, tools, sessions, MCP | MIT; https://github.com/anomalyco/opencode |
| PortableGit | Git, Bash and Unix command-line utilities | GPL-2.0 and included licenses; https://github.com/git-for-windows/git |
| Node.js | JavaScript runtime, npm, npx | MIT and included licenses; https://nodejs.org/ |
| CPython standalone | Python runtime and standard library | Python-2.0 and included licenses; https://github.com/astral-sh/python-build-standalone |
| uv | Python environment / package management | MIT OR Apache-2.0; https://github.com/astral-sh/uv |
| ripgrep | Fast file and text search | MIT OR Unlicense; https://github.com/BurntSushi/ripgrep |

Upstream archives are preserved when assembled, including license files and
third-party notices. OpenCode's MIT notice is additionally included under
licenses/OpenCode-LICENSE. Git for Windows corresponding source and build scripts
are available at the exact release tag v2.56.0.windows.2 in its source repository;
its distributed source archives and individual bundled projects retain their
licenses. This distribution does not relicense those components.

Only the PocketAgent launcher, packaging, defaults and tests use this repository's
MIT license. Optional plugins, MCP servers, packages, and model services that users
add separately retain their own licenses and terms.

