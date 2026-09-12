"""Add resolution verification columns to complaints and images – Phase 6."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_resolution_verification"
down_revision = "0002_sla_ml_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    c_cols = {c["name"] for c in inspector.get_columns("complaints")}
    i_cols = {c["name"] for c in inspector.get_columns("images")}
    c_idxs = {i["name"] for i in inspector.get_indexes("complaints")}
    for col, typ in [("verification_score", sa.Float()), ("verification_status", sa.String(32)),
                     ("verification_details", JSONB), ("verified_at", sa.DateTime(timezone=True)),
                     ("citizen_rating", sa.Integer()), ("citizen_feedback", sa.Text())]:
        if col not in c_cols:
            op.add_column("complaints", sa.Column(col, typ, nullable=True))
    if "ix_complaints_verification_status" not in c_idxs:
        op.create_index("ix_complaints_verification_status", "complaints", ["verification_status"])
    for col, typ in [("latitude", sa.Float()), ("longitude", sa.Float()), ("captured_at", sa.DateTime(timezone=True))]:
        if col not in i_cols:
            op.add_column("images", sa.Column(col, typ, nullable=True))


def downgrade() -> None:
    op.drop_column("images", "captured_at")
    op.drop_column("images", "longitude")
    op.drop_column("images", "latitude")

    op.drop_index("ix_complaints_verification_status", table_name="complaints")
    op.drop_column("complaints", "citizen_feedback")
    op.drop_column("complaints", "citizen_rating")
    op.drop_column("complaints", "verified_at")
    op.drop_column("complaints", "verification_details")
    op.drop_column("complaints", "verification_status")
    op.drop_column("complaints", "verification_score")
