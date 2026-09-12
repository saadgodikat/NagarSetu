"""Add SLA breach prediction columns to complaints table – Phase 3."""

from alembic import op
import sqlalchemy as sa

revision = "0002_sla_ml_columns"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from sqlalchemy import text, inspect
    inspector = inspect(bind)
    existing = {c["name"] for c in inspector.get_columns("complaints")}
    if "breach_probability" not in existing:
        op.add_column("complaints", sa.Column("breach_probability", sa.Float(), nullable=True))
    if "escalation_level" not in existing:
        op.add_column("complaints", sa.Column("escalation_level", sa.String(length=32), nullable=True))
    if "sla_predicted_at" not in existing:
        op.add_column("complaints", sa.Column("sla_predicted_at", sa.DateTime(timezone=True), nullable=True))
    existing_indexes = {i["name"] for i in inspector.get_indexes("complaints")}
    if "ix_complaints_breach_probability" not in existing_indexes:
        op.create_index("ix_complaints_breach_probability", "complaints", ["breach_probability"])
    if "ix_complaints_escalation_level" not in existing_indexes:
        op.create_index("ix_complaints_escalation_level", "complaints", ["escalation_level"])


def downgrade() -> None:
    op.drop_index("ix_complaints_escalation_level", table_name="complaints")
    op.drop_index("ix_complaints_breach_probability", table_name="complaints")
    op.drop_column("complaints", "sla_predicted_at")
    op.drop_column("complaints", "escalation_level")
    op.drop_column("complaints", "breach_probability")
