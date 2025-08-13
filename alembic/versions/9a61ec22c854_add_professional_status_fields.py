"""add professional status fields

Revision ID: 9a61ec22c854
Revises: 25d814bc83ed
Create Date: 2025-08-13 03:40:15.589166
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a61ec22c854"
down_revision: Union[str, None] = "25d814bc83ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to existing users table
    op.add_column("users", sa.Column("location", sa.String(length=120), nullable=True))

    # Safer DB-level defaults for booleans/ints
    op.add_column(
        "users",
        sa.Column("is_professional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "users",
        sa.Column("professional_status_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("professional_upgraded_by_id", postgresql.UUID(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("extra_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Self-referencing FK (who upgraded whom)
    op.create_foreign_key(
        "fk_users_professional_upgraded_by",
        "users",
        "users",
        ["professional_upgraded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FK first, then columns (reverse order is safe)
    op.drop_constraint("fk_users_professional_upgraded_by", "users", type_="foreignkey")
    op.drop_column("users", "extra_fields")
    op.drop_column("users", "professional_upgraded_by_id")
    op.drop_column("users", "professional_status_updated_at")
    op.drop_column("users", "is_professional")
    op.drop_column("users", "location")
