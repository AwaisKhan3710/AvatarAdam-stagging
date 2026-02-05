"""fix_refresh_tokens_schema

Revision ID: fef62c2b46e1
Revises: 323b1add0d9f
Create Date: 2025-12-12 14:23:01.445907

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fef62c2b46e1"
down_revision: Union[str, None] = "323b1add0d9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename token to token_hash
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.alter_column("refresh_tokens", "token", new_column_name="token_hash")
    op.alter_column(
        "refresh_tokens",
        "token_hash",
        type_=sa.String(255),
        existing_type=sa.String(500),
    )
    op.create_index(
        "ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True
    )

    # Add missing columns
    op.add_column(
        "refresh_tokens",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("refresh_tokens", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column(
        "refresh_tokens", sa.Column("ip_address", sa.String(45), nullable=True)
    )


def downgrade() -> None:
    # Remove added columns
    op.drop_column("refresh_tokens", "ip_address")
    op.drop_column("refresh_tokens", "user_agent")
    op.drop_column("refresh_tokens", "revoked_at")

    # Rename token_hash back to token
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.alter_column("refresh_tokens", "token_hash", new_column_name="token")
    op.alter_column(
        "refresh_tokens", "token", type_=sa.String(500), existing_type=sa.String(255)
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)
