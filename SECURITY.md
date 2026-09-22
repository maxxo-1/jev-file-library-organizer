# Security

Please report a vulnerability privately through GitHub's security-advisory feature rather than opening a public issue.

The organizer treats file contents as untrusted evidence, refuses symlinks, checks SHA-256 fingerprints before and after moves, refuses overwrites atomically, and records moves before execution for recovery. Keep `config.json`, `.env`, the state directory and generated dashboard out of commits because they can contain private paths or extracted text.
