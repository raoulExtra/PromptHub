# Extensions

Our goal is to explain why the combination of a well-designed prompt, Python
processing, and a database is so effective for use in an LLM. Prompts provide
clear intent and constraints, Python supplies reliable execution, and the
database preserves structured context and results across interactions.

## Why a DB

A minimal database contains tables and rows. In analogy to Excel, tables are
like tabs, while columns describe the data and rows contain individual records.
This simple structure gives an LLM a predictable, queryable way to work with
prompts and their metadata.

In contrast to Excel, each database column has a datatype, such as `TEXT`,
`INTEGER`, or `DATE`. If, for example, the database contains a prompt table and
a dynamic `tags_registered` table, Python can add useful safeguards—for
example, rejecting an entered tag when it is not registered.

On top of a table, a database view can provide a specialized perspective on
that data without duplicating it. For example, a view can derive a well-formed
system prompt by selecting and ordering prompt records according to their
criticality.

With Python code, a call can expose clear arguments that perform exactly the
intended operation on the database or other parts of the codebase. At the chat level, you describe your
intention, and the model—knowing the Python code and its possible arguments—can
translate an imprecise instruction into solid, reliable actions.

## Prompt types and governance tags

PromptHub supports three prompt types: `System prompt`, `Agent prompt`, and
`User prompt`. Use the type field for primary classification and tags for
additional meaning:

- `governance:system_instruction` → `System prompt`
- `governance:agent_instruction` → `Agent prompt`
- `governance:user_instruction` → `User prompt`

`init_db` registers these governance tags, as well as criticality, demo, task,
and domain tags. Governance tags use orange; `data:demo` uses light blue.

## Generating prompt variants

The CLI writes generated variants to the workspace root:

```bash
python3 extensions/extension.py --gen_prompt sys --min_crit high
# writes SYSTEM.md
python3 extensions/extension.py --gen_prompt user --min_crit normal
# writes USER.md
```

The `sys` variant contains `System prompt` and `Agent prompt` records. The
`user` variant contains only `User prompt` records. Records are ordered from
highest to lowest criticality.

## Assigning tags in the library

Check one or more prompt cards, then choose a tag under **ASSIGN TAG TO PROMPT**.
The tag is assigned to every selected prompt and the list refreshes
automatically. Governance tags warn before automatically changing the prompt
type to the matching type.
