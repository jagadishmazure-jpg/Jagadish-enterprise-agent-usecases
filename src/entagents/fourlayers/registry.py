"""Versioned prompt registry: prompts live as JSON files, are loaded by id and version, and carry a content hash."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

DIR = Path(__file__).parent / "prompts"
REQUIRED = {"id", "version", "changelog", "template", "output_keys", "cite_clause"}


@dataclass(frozen=True)
class Prompt:
    id: str
    version: int
    template: str
    output_keys: tuple
    cite_clause: bool
    changelog: str
    sha: str

    def render(self, invoice: str, policy: str = "(none)") -> str:
        return self.template.format(invoice=invoice, policy=policy)


def load(pid: str, version: int | None = None) -> Prompt:
    found = {}
    for f in DIR.glob(f"{pid}.v*.json"):
        d = json.loads(f.read_text())
        missing = REQUIRED - d.keys()
        if missing:
            raise ValueError(f"{f.name} missing {sorted(missing)}")
        found[d["version"]] = (d, hashlib.sha256(f.read_bytes()).hexdigest()[:12])
    if not found:
        raise KeyError(pid)
    v = max(found) if version is None else version
    if v not in found:
        raise KeyError(f"{pid} v{v}")
    d, sha = found[v]
    return Prompt(d["id"], d["version"], d["template"], tuple(d["output_keys"]), d["cite_clause"], d["changelog"], sha)


def versions(pid: str) -> list[int]:
    return sorted(json.loads(f.read_text())["version"] for f in DIR.glob(f"{pid}.v*.json"))
