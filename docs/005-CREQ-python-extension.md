# CREQ: Python extension database access

## Requirement

Python extension code shall provide safe, reusable access to PromptHub data and
support database initialization and prompt generation.

## Acceptance criteria

- `extensions/extension.py` reads the local database in read-only mode for
  normal read operations.
- `list_tables()` lists user tables.
- `read_table(name)` returns rows from a selected table as dictionaries.
- `read_all_tables()` returns all user tables and their rows.
- `--init_db` creates the schema and seeds demo prompts with varied criticality.
- The extension can invoke the import/export submodule.
- Every executable Python utility provides a `--help` explanation of its
  purpose and available arguments.
