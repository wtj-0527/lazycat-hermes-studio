---
name: lazycat-projected-mcp-configuration
description: Configure discovered LazyCat MCP providers safely.
version: 1.0.0
author: 王.W, Hermes Agent
license: AGPL-3.0
platforms: [linux]
metadata:
  hermes:
    tags: [lazycat, mcp, hermes-studio, coding-agents]
    related_skills: [hermes-agent]
---

# LazyCat Projected MCP Configuration

## Overview

Use this skill inside the LazyCat Hermes Studio application to discover projected MCP Provider resources and configure every provider that actually exists for Hermes Studio and every supported Coding Agent runtime.

The projected resource directory is the source of truth. Never hard-code the current provider count or a fixed provider-name list: installed applications can add or remove providers over time.

## Safety Rules

- Treat `/lzcapp/run/resources/mcp-providers/*/*/mcp.yml` as read-only discovery input.
- Configure a provider only when its projected `mcp.yml` exists and passes validation. Absence means skip, not create a placeholder.
- Build the canonical URL only as `http://app.<package-id>.lzcx<endpoint>`.
- Reject package IDs, endpoints, names, or generated URLs that fail strict validation. Do not guess corrections.
- Keep each provider as an independent MCP server. Do not aggregate tools or protocol traffic.
- Preserve unrelated user MCP entries. Update only an entry previously managed by this procedure or an exact-name entry whose current URL is the same canonical provider URL.
- Never print tickets, API keys, bearer tokens, credential-bearing URLs, or full configuration files.
- Configuration success, MCP protocol reachability, and application/plugin readiness are separate acceptance layers.
- Existing chats and Coding Agent runs may hold immutable configuration snapshots. Validate with a new chat or run.

## Procedure

### 1. Read the current Hermes Studio API contract

Read the current Hermes Studio OpenAPI outline without filters, then inspect the MCP registry, profile, and Coding Agent configuration modules selected from that outline. Do not rely on endpoint shapes copied from an older release.

Completion criterion: the current methods, paths, request bodies, profile scoping rules, and installed Coding Agent identifiers are known before any write.

### 2. Discover and validate projected providers

Enumerate every regular file matching:

```text
/lzcapp/run/resources/mcp-providers/*/*/mcp.yml
```

For each file:

1. Derive `package-id` and `resource-id` from the two path components below `mcp-providers`.
2. Parse YAML; do not extract values with line-oriented text matching.
3. Require a valid provider endpoint beginning with `/` and reject control characters, fragments, userinfo, schemes, or hostnames inside the endpoint.
4. Require the package ID to match the LazyCat package-ID grammar used by the installed wrapper.
5. Generate exactly:

   ```text
   http://app.<package-id>.lzcx<endpoint>
   ```

6. Derive a deterministic server name from projected metadata when a valid name is provided; otherwise use a collision-safe name based on `package-id` and `resource-id`.
7. Reject duplicate names that resolve to different URLs and duplicate URLs that resolve to conflicting metadata.

Do not assume there are thirteen providers. Zero providers is a valid discovery result and must produce zero provider writes.

Completion criterion: a sanitized catalog contains only unique, validated `{name, url, source}` records and no credentials.

### 3. Inspect existing consumers before writing

Discover, rather than assume:

- every Hermes Profile exposed by the current Studio API;
- every installed Coding Agent returned by the current Studio API;
- each installed agent's declared live MCP configuration file or supported configuration API;
- whether the current Ekko run entry point accepts external `mcpServers` or `mcp_servers`.

Known consumer families require different adapters:

| Consumer | Configuration behavior |
|---|---|
| Hermes | Use the Studio MCP registry and include the target Profile header when required by the current API. |
| Claude Code | Merge independent HTTP servers into the declared Claude MCP JSON; preserve all existing keys and entries. |
| Codex | Merge independent URL server tables into the declared Codex TOML; parse before and after writing and avoid duplicate tables. |
| Pi | Merge independent HTTP servers into the Pi MCP JSON consumed by the installed adapter; preserve all existing keys and entries. |
| Ekko | Pass the discovered server map through the run request's external `mcpServers`/`mcp_servers` field. Do not claim that Hermes registry or another agent's file is inherited. |
| Future agents | Configure only when the current Studio API declares a writable MCP-capable config surface and its format can be parsed and verified. Otherwise report `UNSUPPORTED`, without guessing a path or schema. |

A consumer that is not installed must be reported as `SKIPPED_NOT_INSTALLED`, not configured speculatively.

Completion criterion: every installed consumer is mapped to a verified adapter or an explicit unsupported/blocking status.

### 4. Apply idempotent configuration

For each validated provider and consumer:

1. Read and parse the current configuration.
2. Merge the provider without deleting unrelated entries.
3. Use the consumer's supported HTTP transport label (`streamableHttp`, `http`, or URL table) as defined by its current contract.
4. Write atomically where a file-backed adapter is required: write a same-directory temporary file, flush it, replace the destination, and preserve appropriate ownership and permissions.
5. For Hermes, create or patch through the registry API rather than editing its database.
6. For Ekko, inject the complete discovered map into each new run that should receive these providers. If the selected run API cannot carry external MCP servers, stop with `BLOCKED_EKKO_INJECTION_UNAVAILABLE`.

Do not create configuration for missing projected providers. Remove a stale managed entry only when provenance proves it was created by this procedure and the user requested reconciliation; otherwise leave it and report it.

Completion criterion: a second execution produces no semantic configuration change.

### 5. Verify every layer

For every configured consumer, verify:

1. **Saved configuration** — parse and read back the exact server name and canonical URL without printing credentials.
2. **Protocol reachability** — run MCP `initialize` and `tools/list` with the explicit HTTP transport when URL inference is ambiguous.
3. **Consumer visibility** — start a new isolated chat or Coding Agent run and verify that the expected independent servers or tools appear.
4. **Application readiness** — when a provider requires an application plugin, active document, device, or account session, perform a harmless read-only call and report that layer separately.

Never convert a successful `tools/list` into a claim that a plugin, document, device, or account is connected.

Completion criterion: each provider/consumer pair has a final status from this set:

```text
CONFIGURED_AND_VERIFIED
CONFIGURED_PROTOCOL_ONLY
BLOCKED_APPLICATION_NOT_READY
BLOCKED_EKKO_INJECTION_UNAVAILABLE
UNSUPPORTED
SKIPPED_NOT_INSTALLED
SKIPPED_PROVIDER_ABSENT
FAILED
```

## Required Report

Return a compact matrix with one row per provider and consumer containing:

- provider name;
- sanitized canonical host and endpoint;
- consumer;
- configuration status;
- protocol status and discovered tool count;
- consumer-visibility status;
- application-readiness status;
- whether a new run is required;
- a short, non-sensitive error category when blocked.

Also report the number of valid projected providers discovered at execution time. The count is evidence from that run, not a permanent property of this skill.

## Failure Handling

- Invalid YAML or metadata: skip that provider, report its projected source path and validation category, and continue with other independent providers.
- Authentication or ticket failure: stop protocol verification for that provider; do not expose or synthesize credentials.
- JSON/TOML parse failure: do not overwrite the file.
- Profile or API ambiguity: reread the current OpenAPI contract; do not guess.
- Partial write failure: report exact affected consumers and verify that untouched consumers remain unchanged.
- Unsupported future Coding Agent: report it and leave its configuration untouched.
