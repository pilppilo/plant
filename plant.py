#!/usr/bin/env python3
"""Validate a Plant planning directory without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ID_RE = re.compile(r"^(ARCH|ROAD|PHASE|ADR|BENCH|EXP|SCHEM|WORK)-[0-9]{4}$")
ID_FIND_RE = re.compile(r"\b(?:ARCH|ROAD|PHASE|ADR|BENCH|EXP|SCHEM|WORK)-[0-9]{4}\b")
PREFIXES = {
    "architecture": "ARCH", "roadmap": "ROAD", "phase": "PHASE", "decision": "ADR",
    "benchmark": "BENCH", "experiment": "EXP", "schematic": "SCHEM", "workstream": "WORK",
}
STATUSES = {
    "architecture": {"draft", "proposed", "accepted", "rejected", "superseded"},
    "roadmap": {"draft", "proposed", "accepted", "rejected", "superseded"},
    "phase": {"draft", "proposed", "accepted", "ready", "implementing", "implemented", "verified", "blocked", "superseded"},
    "decision": {"proposed", "accepted", "rejected", "superseded"},
    "benchmark": {"draft", "proposed", "accepted", "rejected", "superseded"},
    "experiment": {"draft", "planned", "running", "completed", "abandoned"},
    "schematic": {"draft", "current", "superseded"},
    "workstream": {"active", "closed"},
}
REQUIRED = {"id", "title", "type", "status", "owners", "created", "updated", "depends_on", "supersedes", "related"}
REFERENCE_FIELDS = ("depends_on", "supersedes", "related")
READINESS = {"architecture": "accepted", "roadmap": "accepted", "decision": "accepted", "benchmark": "accepted", "phase": "verified", "experiment": "completed"}
FOCUS_FIELDS = ("Now", "Read", "Workstream", "Next", "Blocked")


def parse_value(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].strip()
        return [] if not items else [item.strip().strip("\"'") for item in items.split(",")]
    return value.strip("\"'")


def frontmatter(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("frontmatter is not closed")
    metadata = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"unsupported frontmatter line: {line}")
        metadata[key.strip()] = parse_value(value)
    return metadata


def table_cells(line: str):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def tables(text: str):
    lines = text.splitlines()
    index = 0
    while index + 1 < len(lines):
        if not (lines[index].lstrip().startswith("|") and lines[index + 1].lstrip().startswith("|")):
            index += 1
            continue
        header, separator = table_cells(lines[index]), table_cells(lines[index + 1])
        if len(header) != len(separator) or not all(re.fullmatch(r":?-{3,}:?", value) for value in separator):
            index += 1
            continue
        index += 2
        rows = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            row = table_cells(lines[index])
            if len(row) == len(header):
                rows.append((index + 1, row))
            index += 1
        yield header, rows


def is_none(value: str):
    return value.strip().rstrip(".").lower() == "none"


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.errors = []
        self.documents = {}

    def error(self, path: Path, message: str):
        self.errors.append({"path": str(path), "message": message})

    def discover(self):
        for path in self.root.rglob("*.md"):
            if "templates" in path.relative_to(self.root).parts:
                continue
            try:
                metadata = frontmatter(path)
            except ValueError as exc:
                self.error(path, str(exc))
                continue
            if metadata is None:
                continue
            missing = REQUIRED - metadata.keys()
            if missing:
                self.error(path, f"missing frontmatter fields: {', '.join(sorted(missing))}")
                continue
            identifier, kind = str(metadata["id"]), metadata["type"]
            if not ID_RE.fullmatch(identifier):
                self.error(path, f"invalid id: {identifier}")
                continue
            if identifier in self.documents:
                self.error(path, f"duplicate id: {identifier}")
                continue
            if kind not in PREFIXES:
                self.error(path, f"unknown type: {kind}")
                continue
            if not identifier.startswith(f"{PREFIXES[kind]}-"):
                self.error(path, f"id {identifier} does not match type {kind}")
            if metadata["status"] not in STATUSES[kind]:
                self.error(path, f"status {metadata['status']} is invalid for {kind}")
            if not path.name.startswith(identifier.lower()):
                self.error(path, f"filename must begin with {identifier.lower()}")
            for field in ("owners", *REFERENCE_FIELDS):
                if not isinstance(metadata[field], list):
                    self.error(path, f"{field} must be a bracketed list")
            self.documents[identifier] = (path, metadata)

    def references(self):
        for identifier, (path, metadata) in self.documents.items():
            for field in REFERENCE_FIELDS:
                values = metadata[field]
                if not isinstance(values, list):
                    continue
                for reference in values:
                    if not ID_RE.fullmatch(reference):
                        self.error(path, f"{field} contains invalid id: {reference}")
                    elif reference not in self.documents:
                        self.error(path, f"{field} references missing document: {reference}")
            dependencies = metadata["depends_on"]
            if isinstance(dependencies, list) and identifier in dependencies:
                self.error(path, "document cannot depend on itself")

    def cycles(self):
        visiting, visited = set(), set()

        def visit(identifier):
            if identifier in visiting:
                self.error(self.documents[identifier][0], f"dependency cycle includes {identifier}")
                return
            if identifier in visited:
                return
            visiting.add(identifier)
            dependencies = self.documents[identifier][1]["depends_on"]
            if isinstance(dependencies, list):
                for dependency in dependencies:
                    if dependency in self.documents:
                        visit(dependency)
            visiting.remove(identifier)
            visited.add(identifier)

        for identifier in self.documents:
            visit(identifier)

    def readiness(self):
        for path, metadata in self.documents.values():
            if metadata["type"] != "phase" or metadata["status"] not in {"ready", "implementing", "implemented", "verified"}:
                continue
            dependencies = metadata["depends_on"]
            if not isinstance(dependencies, list):
                continue
            for dependency_id in dependencies:
                dependency = self.documents.get(dependency_id)
                if dependency is None:
                    continue
                kind, status = dependency[1]["type"], dependency[1]["status"]
                if kind in {"schematic", "workstream"}:
                    self.error(path, f"{kind} {dependency_id} cannot be a phase dependency")
                elif kind in READINESS and status != READINESS[kind]:
                    self.error(path, f"{dependency_id} must be {READINESS[kind]} before this phase is ready")

    def index(self):
        index = self.root / "README.md"
        if not index.exists():
            self.error(index, "missing planning index")
            return
        text = index.read_text(encoding="utf-8")
        indexed, statuses, reservations = set(), {}, set()
        for header, rows in tables(text):
            lookup = {name: position for position, name in enumerate(header)}
            reservation = {"Type", "ID", "Owner", "Purpose", "Reserved at"} <= lookup.keys()
            for line, row in rows:
                if reservation:
                    kind, identifier, owner, purpose, timestamp = (row[lookup[key]] for key in ("Type", "ID", "Owner", "Purpose", "Reserved at"))
                    if not all((kind, identifier, owner, purpose, timestamp)):
                        self.error(index, f"line {line}: incomplete ID reservation")
                    if identifier in reservations:
                        self.error(index, f"line {line}: duplicate ID reservation {identifier}")
                    reservations.add(identifier)
                    if kind not in PREFIXES or not ID_RE.fullmatch(identifier) or not identifier.startswith(f"{PREFIXES.get(kind, '')}-"):
                        self.error(index, f"line {line}: invalid ID reservation {kind} / {identifier}")
                elif "ID" in lookup:
                    found = ID_FIND_RE.findall(row[lookup["ID"]])
                    if found:
                        identifier = found[0]
                        indexed.add(identifier)
                        if "Status" in lookup:
                            statuses[identifier] = row[lookup["Status"]]
        for identifier, (path, metadata) in self.documents.items():
            if identifier not in indexed:
                self.error(path, f"document is not indexed in {index}")
            if identifier in statuses and statuses[identifier] != metadata["status"]:
                self.error(path, f"index status {statuses[identifier]} does not match frontmatter {metadata['status']}")
        for identifier in reservations:
            if identifier in self.documents:
                self.error(index, f"ID reservation {identifier} must be removed when the document is indexed")
        self.focus(index, text)

    def focus(self, index: Path, text: str):
        match = re.search(r"^## Current focus\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE)
        if not match:
            self.error(index, "missing Current focus block")
            return
        fields = {}
        for name, value in re.findall(r"^- \*\*(Now|Read|Workstream|Next|Blocked):\*\*\s*(.*)$", match.group(1), re.MULTILINE):
            identifiers = set(ID_FIND_RE.findall(value))
            if not is_none(value) and not identifiers:
                self.error(index, f"Current focus {name} must contain stable document IDs or None")
            fields[name] = identifiers
        missing = set(FOCUS_FIELDS) - fields.keys()
        if missing:
            self.error(index, f"Current focus is missing fields: {', '.join(sorted(missing))}")
        for name, identifiers in fields.items():
            for identifier in identifiers:
                if identifier not in self.documents:
                    self.error(index, f"Current focus {name} references missing document {identifier}")
        for identifier in fields.get("Now", set()):
            document = self.documents.get(identifier)
            if document and isinstance(document[1]["depends_on"], list):
                absent = set(document[1]["depends_on"]) - fields.get("Read", set())
                if absent:
                    self.error(index, f"Current focus Read is missing direct dependencies of {identifier}: {', '.join(sorted(absent))}")

    def run(self):
        if not self.root.is_dir():
            self.error(self.root, "planning directory does not exist")
            return self.errors
        self.discover()
        self.references()
        self.cycles()
        self.readiness()
        self.index()
        return self.errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Plant planning directory.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable JSON")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="validate a planning directory")
    check.add_argument("plans_dir", type=Path)
    args = parser.parse_args(argv)
    errors = Checker(args.plans_dir).run()
    if args.as_json:
        print(json.dumps({"ok": not errors, "errors": errors}, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"ERROR {error['path']}: {error['message']}")
        print(f"plant check: {len(errors)} error(s)")
    else:
        print("plant check: OK")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
