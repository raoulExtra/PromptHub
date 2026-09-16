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
