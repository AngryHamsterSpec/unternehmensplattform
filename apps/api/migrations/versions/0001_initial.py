"""Erster unveränderlicher Schema- und Rechte-Snapshot."""
from pathlib import Path
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    root = Path(__file__).parent
    for filename in ("0001_schema.sql", "0001_security.sql"):
        op.get_bind().exec_driver_sql((root / filename).read_text("utf8"))
    op.execute("GRANT SELECT ON alembic_version TO platform_app")


def downgrade() -> None:
    raise RuntimeError("Datenhaltige Rückmigration ist absichtlich gesperrt; geprüftes Backup verwenden.")
