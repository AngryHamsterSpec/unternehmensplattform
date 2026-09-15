"""Additiver M2-Snapshot: vorhandene Daten und Initialmigration bleiben erhalten."""
from pathlib import Path
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(Path(__file__).with_name("0002_data.sql").read_text("utf8"))


def downgrade() -> None:
    raise RuntimeError("Datenhaltige Rückmigration ist gesperrt; geprüftes Backup verwenden.")
