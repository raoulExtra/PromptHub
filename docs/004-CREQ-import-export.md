# CREQ: Markdown import and export

## Requirement

Prompts shall be transferable between the database and Markdown files using the
protected import and export folders.

## Acceptance criteria

- Import reads `.md` files from `protected/import/`.
- `--contain <name_part>` limits imports to filenames containing that text.
- Markdown front matter can preserve title, type, favorite status, and tags.
- Export writes one Markdown file per prompt to `protected/export/`.
- Export filenames use the format `###-<prompt-name>.md`, with lowercase
  hyphenated names.
- Demo export only includes prompts tagged `data:demo`.
- Demo export warns when no matching demo prompts exist.
- Before export, stale files are removed while the safety prompt file is kept.
