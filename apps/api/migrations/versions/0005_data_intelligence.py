"""M2-Analysen, Quellenaufträge und unveränderliche Qualitätsregeln."""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        Path(__file__).with_name("0005_data_intelligence.sql").read_text("utf8")
    )


def downgrade() -> None:
    raise RuntimeError("Datenhaltige Rückmigration gesperrt; geprüftes Backup verwenden.")
