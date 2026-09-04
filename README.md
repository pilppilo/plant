# Plant

Plant is a lightweight, repository-native planning protocol for complex
software projects developed by humans and coding agents together.

It keeps architecture, decisions, implementation phases, experiments,
benchmarks, schematics, and workstream notes distinct so that proposals do not
quietly become requirements and implementation activity does not get mistaken
for verified completion.

Plant is documentation-first. Its Markdown files remain readable without a
special service, database, or application.

## Check plans

Run the dependency-free checker before accepting planning changes:

```bash
./plant check path/to/plans
./plant --json check path/to/plans
```

It checks the current tree for ID and reservation collisions, metadata and
filename consistency, missing references, dependency cycles and readiness,
index/status drift, and the Current focus reading route. It does not infer
status transitions or evidence from Git history.

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
2. Copy `schema/metadata.schema.json` to `plans/schema/metadata.schema.json`.
3. Start `plans/README.md` from `templates/index.md`, and copy only the
   needed templates to `plans/templates/`.
4. Merge the Plant instructions from `AGENTS.md` into the repository's
   existing `AGENTS.md`; preserve its repository-specific instructions.
5. Make the `plant` command available, or invoke this checkout's
   `./plant check /path/to/plans` before accepting plan changes.
6. Record the governing architecture and first accepted decisions.
7. Add phase plans only after their architectural dependencies are accepted.

The protocol deliberately does not prescribe a particular issue tracker,
version-control host, agent framework, or product architecture.

## Repository contents

```text
PROTOCOL.md                 governing planning protocol
AGENTS.md                   instructions for agents working on Plant
templates/                  reusable Markdown templates for every document type
schema/metadata.schema.json frontmatter metadata schema
plant, plant.py              dependency-free `plant check` command
example/plans/README.md     example authoritative plan index
```
