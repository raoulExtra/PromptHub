# CREQ: Prompt CRUD

## Requirement

The application shall store prompts locally and provide API operations to create,
list, update, and delete them.

## Acceptance criteria

- `POST /api/prompts` creates a prompt with title, body, favorite status, category, and tags.
- `GET /api/prompts` returns stored prompts with their metadata and derived criticality.
- `PUT /api/prompts/{id}` updates the prompt body.
- `DELETE /api/prompts/{id}` removes the selected prompt.
- Prompt titles remain unique in the database.
- Prompt data persists in the local SQLite database.
