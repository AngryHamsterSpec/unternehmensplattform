"""Importoptionen je Auftrag; vorhandene Originale und Versionen bleiben erhalten."""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        Path(__file__).with_name("0004_csv_options.sql").read_text("utf8")
    )


def downgrade() -> None:
    raise RuntimeError("Datenhaltige Rückmigration ist gesperrt; geprüftes Backup verwenden.")
