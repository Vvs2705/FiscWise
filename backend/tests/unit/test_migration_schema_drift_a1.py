"""A1: a migration o1a7bc49gk6 fica alinhada com os modelos.

Colunas que ela cria existem no modelo, índices que ela cria são os que o
modelo declara (index=True) e os índices duplicados que ela remove não voltam
via create_all.
"""

import importlib.util
from pathlib import Path

import app.main  # noqa: F401  registra todos os modelos
from app.models.base import Base

MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "o1a7bc49gk6_schema_drift_e_indices_fk.py"


def _load():
    spec = importlib.util.spec_from_file_location("mig_a1", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_colunas_criadas_existem_no_modelo_como_not_null():
    mig = _load()
    for table, column in mig.MISSING_COLUMNS:
        col = Base.metadata.tables[table].c[column]
        assert col.nullable is False, (table, column)


def test_indices_de_fk_sao_os_que_o_modelo_declara():
    mig = _load()
    for name, table, column in mig.FK_INDEXES:
        t = Base.metadata.tables[table]
        assert t.c[column].foreign_keys, (table, column)
        assert any(i.name == name and [c.name for c in i.columns] == [column] for i in t.indexes), name


def test_indices_duplicados_nao_sao_recriados_pelo_modelo():
    mig = _load()
    for name, table, column, constraint in mig.DUPLICATE_INDEXES:
        t = Base.metadata.tables[table]
        assert name not in {i.name for i in t.indexes}, name
        uniques = {c.name: [col.name for col in c.columns] for c in t.constraints if c.__class__.__name__ == "UniqueConstraint"}
        assert uniques.get(constraint) == [column], (table, constraint)


def test_migration_encadeada_no_head_anterior():
    mig = _load()
    assert mig.down_revision == "n9h6ab38fj5"
