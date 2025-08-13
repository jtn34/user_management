"""add professional status fields

Revision ID: 9a61ec22c854
Revises: 25d814bc83ed
Create Date: 2025-08-13 03:40:15.589166
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9a61ec22c854"
down_revision: Union[str, None] = "25d814bc83ed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("users")}
    existing_fks = {fk.get("name") for fk in insp.get_foreign_keys("users")}

    # Only add if missing (some envs already have these from the initial migration)
    if "location" not in existing_cols:
        op.add_column("users", sa.Column("location", sa.String(length=120), nullable=True))

    # Skip is_professional if the initial migration already created it
    if "is_professional" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("is_professional", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if "professional_status_updated_at" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("professional_status_updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "professional_upgraded_by_id" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("professional_upgraded_by_id", postgresql.UUID(), nullable=True),
        )

    if "extra_fields" not in existing_cols:
        op.add_column(
            "users",
            sa.Column("extra_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # Create the self-FK only if it doesn't exist
    if "fk_users_professional_upgraded_by" not in (existing_fks - {None}):
        op.create_foreign_key(
            "fk_users_professional_upgraded_by",
            "users",
            "users",
            ["professional_upgraded_by_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Be defensive: drop FK/columns only if they exist
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing_cols = {c["name"] for c in insp.get_columns("users")}
    existing_fks = {fk.get("name") for fk in insp.get_foreign_keys("users")}

    if "fk_users_professional_upgraded_by" in (existing_fks - {None}):
        op.drop_constraint("fk_users_professional_upgraded_by", "users", type_="foreignkey")

    for col in ("extra_fields", "professional_upgraded_by_id", "professional_status_updated_at", "is_professional", "location"):
        if col in existing_cols:
            op.drop_column("users", col)
