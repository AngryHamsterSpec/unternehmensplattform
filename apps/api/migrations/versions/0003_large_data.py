"""Additive Migration für abschnittsweise Speicherung und Worker-Leases."""

from pathlib import Path
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(Path(__file__).with_name("0003_large_data.sql").read_text("utf8"))


def downgrade() -> None:
    raise RuntimeError("Datenhaltige Rückmigration ist gesperrt; geprüftes Backup verwenden.")
