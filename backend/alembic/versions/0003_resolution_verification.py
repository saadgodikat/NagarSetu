"""Add resolution verification columns to complaints and images – Phase 6."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_resolution_verification"
down_revision = "0002_sla_ml_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Complaints table verification fields
    op.add_column("complaints", sa.Column("verification_score", sa.Float(), nullable=True))
    op.add_column("complaints", sa.Column("verification_status", sa.String(length=32), nullable=True))
    op.add_column("complaints", sa.Column("verification_details", JSONB, nullable=True))
    op.add_column("complaints", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("complaints", sa.Column("citizen_rating", sa.Integer(), nullable=True))
    op.add_column("complaints", sa.Column("citizen_feedback", sa.Text(), nullable=True))

    op.create_index("ix_complaints_verification_status", "complaints", ["verification_status"])

    # Images table location & capture metadata
    op.add_column("images", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("images", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column("images", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))


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
