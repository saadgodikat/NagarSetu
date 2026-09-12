"""Add SLA breach prediction columns to complaints table – Phase 3."""

from alembic import op
import sqlalchemy as sa

revision = "0002_sla_ml_columns"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("breach_probability", sa.Float(), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("escalation_level", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("sla_predicted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Index for fast filtering on high-risk complaints in admin dashboard
    op.create_index(
        "ix_complaints_breach_probability",
        "complaints",
        ["breach_probability"],
    )
    op.create_index(
        "ix_complaints_escalation_level",
        "complaints",
        ["escalation_level"],
    )


def downgrade() -> None:
    op.drop_index("ix_complaints_escalation_level", table_name="complaints")
    op.drop_index("ix_complaints_breach_probability", table_name="complaints")
    op.drop_column("complaints", "sla_predicted_at")
    op.drop_column("complaints", "escalation_level")
    op.drop_column("complaints", "breach_probability")
