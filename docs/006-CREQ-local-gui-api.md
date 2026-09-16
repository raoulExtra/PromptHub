# CREQ: Local GUI and API boundary

## Requirement

The desktop GUI shall communicate with a local FastAPI service and keep prompt
data on the user’s machine.

## Acceptance criteria

- The GUI is served from the local application and API at `127.0.0.1:8000`.
- Static frontend files are served by FastAPI.
- The frontend uses HTTP API calls for prompt operations and filtering.
- No cloud service is required for normal prompt storage or retrieval.
- API responses expose prompt metadata needed by the library and agent feed.
