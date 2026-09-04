# Plant

Plant is a lightweight, repository-native planning protocol for complex
software projects developed by humans and coding agents together.

It keeps architecture, decisions, implementation phases, experiments,
benchmarks, schematics, and workstream notes distinct so that proposals do not
quietly become requirements and implementation activity does not get mistaken
for verified completion.

Plant is documentation-first. Its Markdown files remain readable without a
special service, database, or application.

## What Plant provides

- A clear authority and precedence model.
- Stable, searchable document identifiers.
- Status lifecycles appropriate to each document type.
- Traceability from architecture through implementation and evidence.
- Append-friendly coordination conventions for multiple agents.
- Templates for architecture, phases, decisions, experiments, benchmarks,
  schematics, and workstreams.
- A machine-readable schema for frontmatter metadata.

## Adopt Plant in a repository

1. Copy `PROTOCOL.md` to the repository's `plans/PROTOCOL.md`.
2. Start its `plans/README.md` from `templates/index.md`.
3. Copy only the document templates the project needs.
4. Record the governing architecture and first accepted decisions.
5. Add phase plans only after their architectural dependencies are accepted.

The protocol deliberately does not prescribe a particular issue tracker,
version-control host, agent framework, or product architecture.

## Repository contents

```text
PROTOCOL.md                 governing planning protocol
AGENTS.md                   instructions for agents working on Plant
templates/                  reusable Markdown templates for every document type
schema/metadata.schema.json frontmatter metadata schema
example/plans/README.md     example authoritative plan index
```
