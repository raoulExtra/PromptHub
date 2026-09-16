# CREQ: Database and registered tags

## Requirement

Prompt metadata shall be stored in SQLite with explicit column types and a
registered-tag table for controlled tag vocabulary.

## Acceptance criteria

- The `PromptHub` table stores prompt identity, body, date, favorite status,
  category, and tags.
- The database uses typed columns such as `TEXT`, `INTEGER`, and `DATE`.
- `init_db` creates `tags_registered` if it does not exist.
- The registered demo vocabulary includes all supported criticality tags and
  `data:demo`.
- Initialization is safe to repeat and does not duplicate registered tags or
  seeded prompt titles.
- The `agent_prompts` view derives criticality ordering without duplicating
  prompt records.
