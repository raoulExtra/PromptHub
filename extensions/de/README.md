# Erweiterungen

Unser Ziel ist es zu erklären, warum das Zusammenspiel aus einem gut gestalteten
Prompt, der Verarbeitung mit Python und einer Datenbank so wirkungsvoll für die
Nutzung in einem LLM ist.
Prompts geben klare Absichten und Einschränkungen vor, Python sorgt für eine
zuverlässige Ausführung, und die Datenbank bewahrt strukturierten Kontext sowie
Ergebnisse über mehrere Interaktionen hinweg.

## Warum eine Datenbank?

Eine minimale Datenbank besteht aus Tabellen und Zeilen. Als Analogie zu Excel
kann man Tabellen mit Registerkarten vergleichen: Spalten beschreiben die Daten
und Zeilen enthalten einzelne Datensätze. Diese einfache Struktur bietet einem
LLM eine vorhersehbare und abfragbare Möglichkeit, mit Prompts und ihren
Metadaten zu arbeiten.

Im Gegensatz zu Excel besitzt jede Datenbankspalte einen Datentyp, zum Beispiel
`TEXT`, `INTEGER` oder `DATE`. Wenn die Datenbank beispielsweise eine Prompt-
Tabelle und eine dynamische Tabelle `tags_registered` enthält, kann Python
sinnvolle Schutzmechanismen hinzufügen—etwa ein eingegebenes Tag abzulehnen,
wenn es nicht registriert ist.

Auf einer Tabelle kann eine Datenbank-View eine spezialisierte Sicht auf die
Daten bereitstellen, ohne sie zu duplizieren. Eine View kann zum Beispiel einen
gut strukturierten System-Prompt ableiten, indem sie Prompt-Datensätze anhand
ihrer Kritikalität auswählt und sortiert.

## Prompt-Typen und Governance-Tags

PromptHub unterstützt drei Prompt-Typen: `System prompt`, `Agent prompt` und
`User prompt`. Der Typ dient zur grundlegenden Einordnung; Tags beschreiben
zusätzliche Eigenschaften:

- `governance:system_instruction` → `System prompt`
- `governance:agent_instruction` → `Agent prompt`
- `governance:user_instruction` → `User prompt`

`init_db` registriert diese Governance-Tags sowie Kritikalitäts-, Demo-, Task-
und Domain-Tags. Governance-Tags werden orange dargestellt, `data:demo` hellblau.

## Prompt-Varianten erzeugen

Die CLI schreibt erzeugte Varianten in das Workspace-Hauptverzeichnis:

```bash
python3 extensions/extension.py --gen_prompt sys --min_crit high
# schreibt SYSTEM.md
python3 extensions/extension.py --gen_prompt user --min_crit normal
# schreibt USER.md
```

Die Variante `sys` enthält `System prompt`- und `Agent prompt`-Datensätze.
Die Variante `user` enthält ausschließlich `User prompt`-Datensätze. Die
Datensätze werden nach Kritikalität absteigend sortiert.

## Tags in der Bibliothek zuweisen

Wähle eine oder mehrere Prompt-Karten aus und anschließend ein Tag unter
**ASSIGN TAG TO PROMPT**. Das Tag wird allen ausgewählten Prompts zugewiesen;
die Liste wird automatisch aktualisiert. Bei Governance-Tags erscheint eine
Warnung, bevor der Prompt-Typ automatisch angepasst wird.
