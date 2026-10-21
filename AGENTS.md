# PocketAgent maintenance

This repository packages existing software for portable Windows use. It does not
implement an agent loop, model client, editing tools, shell tools, or MCP server.
Reuse OpenCode for those capabilities. Keep first-party code limited to portable
launching, dependency packaging, configuration and integration tests.

Target Windows 10/11 x64 without installation or administrator privileges.
Resolve paths from the executable, never from the current working directory or
a recorded drive letter. Do not overwrite HOME, USERPROFILE or machine settings.
Keep user credentials and sessions under data/, excluded from Git and releases.
Preserve upstream licenses and verify every downloaded binary against its pinned
SHA256 before extracting or executing it.

Run the real upstream binary in integration tests. Report synthetic-provider tests
separately from tests against a real, paid model. Never claim Windows validation
from Linux-only testing. Release only after the Windows integration checks pass.

