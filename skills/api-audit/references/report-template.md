# <API name> audit - YYYY-MM-DD

## Scope

- **Environment**: test / live (read-only) / both
- **Base URL variable**: `<ENV_VAR_NAME>` (no hostnames or credentials here)
- **API version**: <version, or "unversioned">
- **Sources compared**: docs (dated), OpenAPI spec, Postman collection, SDK
- **Results file**: `results/<date>.json`

## Summary

Three to five lines: what works as documented, what doesn't, and what the
integration must work around.

## Endpoints

| Method | Path | Documented | Observed | Notes |
|---|---|---|---|---|
| GET | /items/{id} | yes | works | pagination uses `offset`, docs say `page` |
| PUT | /items/{id} | yes | partial | see field matrix |
| POST | /items/search | no | works | found in the SDK, not the docs |

## Field matrix

| Object | Field | Read | Write | Outcome detail | Variants tried |
|---|---|---|---|---|---|
| item | name | yes | writable | trimmed to 120 chars | - |
| item | custom_3 | always empty | ignored | 200, value unchanged | string, number, nested, PATCH |

## Documented versus observed

- <Doc claim>. Observed: <behaviour>. Evidence: request ID `<id>`, <timestamp>.

## Rate limits and errors

- Limits hit, headers returned, retry behaviour, error format.

## Open questions for the vendor

1. <Question>, ticket #<n>

## Workarounds in our integration

- <Behaviour>, handled by <approach>, recorded in <ADR or code reference>.
