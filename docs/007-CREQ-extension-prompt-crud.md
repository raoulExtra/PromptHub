# CREQ: Extension prompt CRUD with tags

## Requirement

`extensions/extension.py` shall support creating, reading, updating, and
deleting prompts through command-line arguments, including their tags.

## Acceptance criteria

- The extension provides command-line operations for prompt create, read, update,
  and delete.
- Create accepts a title, body, category, favorite status, and zero or more tags.
- Read can retrieve one prompt, filtered prompts, or all prompts.
- Update can change prompt content and replace or update its tags.
- Delete removes the selected prompt by ID or another documented stable identity.
- Tags are normalized consistently and criticality tags are preserved.
- Registered-tag safeguards can reject tags that are not present in
  `tags_registered` when validation is enabled.
- Every CRUD operation reports success or a clear error through the CLI.
- The operations are documented by `python3 extensions/extension.py --help`.
