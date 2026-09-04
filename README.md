# Plant

Plant is a lightweight, repository-native planning protocol for complex
software projects developed by humans and coding agents together.

It keeps architecture, decisions, implementation phases, experiments,
benchmarks, schematics, and workstream notes distinct so that proposals do not
quietly become requirements and implementation activity does not get mistaken
for verified completion.

Plant is documentation-first. Its Markdown files remain readable without a
special service, database, or application.

## Commands

Run the dependency-free checker before accepting planning changes:

```bash
./plant check path/to/plans
./plant --json check path/to/plans
python3 -m unittest discover -s tests -v
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
- Templates for architecture, roadmaps, phases, decisions, experiments,
  benchmarks, schematics, and workstreams.
- A machine-readable schema for frontmatter metadata.

## Adopt Plant in a repository

From the independent Plant checkout, create a pinned snapshot:

```bash
/path/to/plant/plant init /path/to/project/plans
```

This copies `PROTOCOL.md`, the metadata schema, and templates unchanged. It
creates `plans/README.md` from the index template, records the source revision,
and writes `plans/.plant-lock.json`. It does not copy Plant's checker, tests,
or examples; create project-specific planning documents from the copied
templates.

Add Plant's short instruction block from `AGENTS.md` to the consuming
repository's existing `AGENTS.md`, preserving repository-specific instructions.
Run the independent checker after planning changes:

```bash
/path/to/plant/plant check /path/to/project/plans
```

To update the upstream-managed snapshot later, first preview it:

```bash
/path/to/plant/plant update /path/to/project/plans --dry-run
/path/to/plant/plant update /path/to/project/plans
```

`update` replaces only files unchanged since the last sync. It refuses to
overwrite modified or deleted managed files, leaving conflicts for a deliberate
manual merge. It never changes project planning documents or `AGENTS.md`; it
only refreshes the source-revision line in the plan index and the lock file.

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
