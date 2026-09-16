# CREQ: Registered-tag CRUD

## Requirement

`extensions/extension.py` shall support creating, reading, updating, and
deleting entries in the `tags_registered` table through command-line arguments.

## Acceptance criteria

- The extension can create a registered tag.
- The extension can list all registered tags or read one tag.
- The extension can rename a registered tag.
- The extension can delete a registered tag.
- Duplicate tag names are rejected with a clear error.
- Tag names are compared case-insensitively while preserving their display case.
- Prompt CRUD validation uses the current registered-tag table.
- Every operation is documented by `python3 extensions/extension.py --help`.
