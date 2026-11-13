"""Migrations: cada revision é única e a cadeia tem uma só ponta (head).

Duas threads chegaram a criar migrations com o mesmo id; o Alembic não acusa
isso localmente, mas o upgrade em produção falha.
"""

import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def _revisions():
    out = []
    for f in sorted(VERSIONS.glob("*.py")):
        s = f.read_text(encoding="utf-8")
        rev = re.search(r"^revision(?:\s*:\s*\w+)?\s*=\s*['\"]([^'\"]+)", s, re.M)
        down = re.search(r"^down_revision(?:\s*:[^=]+)?\s*=\s*(.+)$", s, re.M)
        if rev:
            out.append((f.name, rev.group(1), re.findall(r"['\"]([^'\"]+)['\"]", down.group(1)) if down else []))
    return out


def test_revision_ids_unicos():
    seen = {}
    for name, rev, _ in _revisions():
        assert rev not in seen, f"revision {rev} repetida em {seen[rev]} e {name}"
        seen[rev] = name


def test_uma_so_head():
    revs = _revisions()
    downs = {d for _, _, ds in revs for d in ds}
    heads = [rev for _, rev, _ in revs if rev not in downs]
    assert len(heads) == 1, f"mais de uma head: {heads}"
