"""The Alembic migrations must build exactly the schema described by the models."""
import pathlib

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.database import Base

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def test_upgrade_head_matches_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_alembic_config(url), "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert diff == []
    finally:
        engine.dispose()


def test_downgrade_base_removes_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = _alembic_config(url)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_from_0001_preserves_responsibilities(tmp_path):
    from sqlalchemy import text

    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    config = _alembic_config(url)
    command.upgrade(config, "0001")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO service_units (id, code, name) VALUES ('unit-syn-001', 'USYN', 'Synthetic Unit')"))
            connection.execute(text(
                "INSERT INTO service_responsibilities (id, user_id, service_unit_id, role_title, status) "
                "VALUES ('resp-syn-001', 'usr-syn-001', 'unit-syn-001', 'Coordinator', 'ACTIVE')"))
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT id, user_id, service_unit_id FROM service_responsibilities")).all()
        column = {c["name"]: c for c in inspect(engine).get_columns("service_responsibilities")}["user_id"]
    finally:
        engine.dispose()
    assert rows == [("resp-syn-001", "usr-syn-001", "unit-syn-001")]
    assert column["type"].length == 50
