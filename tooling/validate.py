#!/usr/bin/env python3
"""HATO Festival Config validator.

Run from the repo root (or pass the root as argv[1]):

    python3 tooling/validate.py

Performs, in order:
  1. CONTRACT GUARD  — frozen files manifest.json + krishna_matki.json must exist at root
  2. JSON PARSE      — every *.json in the repo must parse
  3. SCHEMA          — v1 campaigns, v2 master manifests, v2 section manifests
  4. SEMANTIC        — window sanity, hex colors, badge math, campaignId, section/filename match
  5. FORBIDDEN SCAN  — plaintext http, foreign hosts, script URIs, secret-shaped tokens

Exit code 0 = everything green; 1 = at least one failure (all failures listed).
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("ERROR: jsonschema not installed. Run: python -m pip install jsonschema")
    sys.exit(2)

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent

V1_FILES = [
    "manifest.json",
    "janmashtami.json",
    "diwali.json",
    "ganeshotsav.json",
    "navratri.json",
    "christmas.json",
]
MASTER_FILES = ["master_manifest.json", "master_manifest.dev.json"]

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
ALLOWED_HOST = "raw.githubusercontent.com"
ALLOWED_PATH_PREFIX = "/metavisionrs/"
# Built by concatenation so this file never trips its own scan if ever included.
SECRET_PATTERNS = ["xox", "gh" + "p_", "AK" + "IA"]
SCRIPT_URI = "java" + "script:"
PLAIN_HTTP = "http" + "://"
DRAFT07_URI = "http://json-schema.org/draft-07/schema#"

failures: list[str] = []
passes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def ok(msg: str) -> None:
    passes.append(msg)


# ---------------------------------------------------------------- 1. contract guard
def contract_guard() -> None:
    for frozen in ("manifest.json", "krishna_matki.json"):
        if (ROOT / frozen).is_file():
            ok(f"contract-guard: {frozen} present at root")
        else:
            fail(f"contract-guard: FROZEN file /{frozen} is MISSING at repo root — "
                 "this breaks the live production campaign")


# ---------------------------------------------------------------- 2. json parse
def all_json_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.json") if ".git" not in p.parts)


def parse_all() -> dict:
    docs = {}
    for p in all_json_files():
        rel = p.relative_to(ROOT).as_posix()
        try:
            docs[rel] = json.loads(p.read_text(encoding="utf-8"))
            ok(f"parse: {rel}")
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            fail(f"parse: {rel} is not valid JSON: {e}")
    return docs


# ---------------------------------------------------------------- 3. schema validation
def load_schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def validate_schema(docs: dict) -> None:
    v1 = load_schema("campaign.v1.schema.json")
    master = load_schema("master-manifest.v2.schema.json")
    section = load_schema("section-manifest.v2.schema.json")

    def run(rel: str, schema: dict, label: str) -> None:
        if rel not in docs:
            fail(f"schema[{label}]: {rel} missing or unparseable")
            return
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(validator.iter_errors(docs[rel]), key=lambda e: list(e.absolute_path))
        if errors:
            for e in errors[:5]:
                path = "/".join(str(x) for x in e.absolute_path) or "<root>"
                fail(f"schema[{label}]: {rel} @ {path}: {e.message}")
        else:
            ok(f"schema[{label}]: {rel}")

    for rel in V1_FILES:
        run(rel, v1, "v1")
    for rel in MASTER_FILES:
        run(rel, master, "master-v2")
    for p in sorted((ROOT / "sections").glob("*.json")):
        run(p.relative_to(ROOT).as_posix(), section, "section-v2")


# ---------------------------------------------------------------- 4. semantic checks
def check_window(rel: str, doc: dict) -> None:
    try:
        starts = datetime.fromisoformat(doc["startsAt"])
        ends = datetime.fromisoformat(doc["endsAt"])
    except (KeyError, ValueError) as e:
        fail(f"semantic: {rel} startsAt/endsAt unparseable: {e}")
        return
    if starts >= ends:
        fail(f"semantic: {rel} startsAt ({doc['startsAt']}) must be BEFORE endsAt ({doc['endsAt']})")
    else:
        ok(f"semantic: {rel} window startsAt < endsAt")


def check_hex_colors(rel: str, theme: dict) -> None:
    bad = [f"{k}={v!r}" for k, v in (theme or {}).items()
           if not (isinstance(v, str) and HEX_RE.match(v))]
    if bad:
        fail(f"semantic: {rel} theme has non-#RRGGBB colors: {', '.join(bad)}")
    else:
        ok(f"semantic: {rel} theme colors are #RRGGBB")


def check_badge(rel: str, where: str, badge) -> None:
    if not isinstance(badge, dict):
        return
    mrp, price = badge.get("mrp"), badge.get("price")
    if isinstance(mrp, (int, float)) and isinstance(price, (int, float)) and price > mrp:
        fail(f"semantic: {rel} {where} badge price ({price}) > mrp ({mrp})")


def check_campaign_id(rel: str, doc: dict) -> None:
    cid = doc.get("campaignId")
    if not isinstance(cid, str) or not cid.strip():
        fail(f"semantic: {rel} campaignId must be a non-empty string")
    else:
        ok(f"semantic: {rel} campaignId non-empty")


def semantic_checks(docs: dict) -> None:
    for rel in V1_FILES:
        doc = docs.get(rel)
        if not isinstance(doc, dict):
            continue
        check_campaign_id(rel, doc)
        check_window(rel, doc)
        check_hex_colors(rel, doc.get("theme", {}))
        for i, tile in enumerate(doc.get("collections", []) or []):
            if isinstance(tile, dict):
                check_badge(rel, f"collections[{i}]", tile.get("badge"))

    for rel in MASTER_FILES:
        doc = docs.get(rel)
        if not isinstance(doc, dict):
            continue
        check_campaign_id(rel, doc)
        check_window(rel, doc)
        check_hex_colors(rel, doc.get("theme", {}))

    for p in sorted((ROOT / "sections").glob("*.json")):
        rel = p.relative_to(ROOT).as_posix()
        doc = docs.get(rel)
        if not isinstance(doc, dict):
            continue
        expected = p.stem
        if doc.get("section") != expected:
            fail(f"semantic: {rel} 'section' field is {doc.get('section')!r} "
                 f"but filename requires {expected!r}")
        else:
            ok(f"semantic: {rel} section field matches filename")
        check_hex_colors(rel, doc.get("theme", {}))
        for i, block in enumerate(doc.get("blocks", []) or []):
            if isinstance(block, dict):
                check_badge(rel, f"blocks[{i}]", block.get("badge"))


# ---------------------------------------------------------------- 5. forbidden patterns
URL_RE = re.compile(r"https?://([^/\s\"']+)(/[^\s\"']*)?")


def forbidden_scan() -> None:
    targets = all_json_files() + sorted(
        p for p in ROOT.rglob("*.rfwtxt") if ".git" not in p.parts
    )
    for p in targets:
        rel = p.relative_to(ROOT).as_posix()
        text = p.read_text(encoding="utf-8", errors="replace")
        # The draft-07 meta-schema URI is a spec-mandated identifier, not a fetchable link.
        cleaned = text.replace(DRAFT07_URI, "")
        # Un-escape regex patterns inside schema files so URL hosts are comparable.
        cleaned = cleaned.replace("\\\\", "").replace("\\", "")

        if PLAIN_HTTP in cleaned:
            fail(f"forbidden: {rel} contains plaintext '{PLAIN_HTTP}' URL (HTTPS only)")
        if SCRIPT_URI in cleaned.lower():
            fail(f"forbidden: {rel} contains '{SCRIPT_URI}' URI")
        for pat in SECRET_PATTERNS:
            if pat in cleaned:
                fail(f"forbidden: {rel} contains secret-shaped token '{pat}…' — "
                     "this repo is public; never commit credentials")
        # Legacy RFW template predates the allowlist and carries example.com in
        # comments only; it stays exempt from the HOST check (still scanned above).
        if p.suffix != ".rfwtxt":
            for m in URL_RE.finditer(cleaned):
                host, path = m.group(1), m.group(2) or ""
                if host != ALLOWED_HOST or not path.startswith(ALLOWED_PATH_PREFIX):
                    fail(f"forbidden: {rel} references disallowed host/path "
                         f"'{m.group(0)[:80]}' (only https on {ALLOWED_HOST}{ALLOWED_PATH_PREFIX}* allowed)")
        ok(f"forbidden-scan: {rel} clean")


# ---------------------------------------------------------------- main
def main() -> int:
    contract_guard()
    docs = parse_all()
    validate_schema(docs)
    semantic_checks(docs)
    forbidden_scan()

    print(f"PASS  {len(passes)} checks")
    if failures:
        print(f"FAIL  {len(failures)} problems:")
        for f_ in failures:
            print(f"  ✗ {f_}")
        return 1
    print("ALL GREEN — config repo is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
