# CREQ: Criticality-aware system and agent prompts

## Requirement

System and agent prompts shall be selectable by criticality tags and returned in
priority order for reliable prompt assembly.

## Acceptance criteria

- Supported levels are `normal`, `low`, `medium`, `high`, and `critical`.
- Tags use the form `criticality:<level>`.
- `GET /api/prompts/agent` returns only system/agent prompts.
- Results are ordered from highest to lowest criticality.
- `GET /api/prompts/agent?criticality=<level>` filters to that exact level.
- `python3 extensions/extension.py --gen_sys_prompt --min_crit high` combines
  prompt contents at `high` or higher.
- A prompt without a recognized criticality tag is treated as `normal`.
