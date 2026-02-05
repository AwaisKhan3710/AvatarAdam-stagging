"""fix_users_schema

Revision ID: 323b1add0d9f
Revises: 001_initial
Create Date: 2025-12-12 14:16:14.024386

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "323b1add0d9f"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename full_name to first_name and add last_name
    op.alter_column("users", "full_name", new_column_name="first_name")
    op.alter_column(
        "users",
        "first_name",
        type_=sa.String(100),
        nullable=False,
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.add_column(
        "users",
        sa.Column("last_name", sa.String(100), nullable=False, server_default=""),
    )

    # Add is_verified column
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Update role enum to match the model
    # First, create the new enum type
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute(
        "CREATE TYPE userrole AS ENUM ('super_admin', 'dealership_admin', 'user')"
    )

    # Update the column to use the new enum
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'admin' THEN 'super_admin'::userrole
            WHEN role::text = 'dealer_principal' THEN 'dealership_admin'::userrole
            WHEN role::text = 'fi_manager' THEN 'user'::userrole
            ELSE 'user'::userrole
        END
    """)

    # Drop old enum type
    op.execute("DROP TYPE userrole_old")

    # Add index on role column
    op.create_index("ix_users_role", "users", ["role"])

    # Remove server_default from last_name after data migration
    op.alter_column("users", "last_name", server_default=None)


def downgrade() -> None:
    # Remove index on role
    op.drop_index("ix_users_role", table_name="users")

    # Revert role enum
    op.execute("ALTER TYPE userrole RENAME TO userrole_new")
    op.execute(
        "CREATE TYPE userrole AS ENUM ('admin', 'dealer_principal', 'fi_manager')"
    )
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'super_admin' THEN 'admin'::userrole
            WHEN role::text = 'dealership_admin' THEN 'dealer_principal'::userrole
            WHEN role::text = 'user' THEN 'fi_manager'::userrole
            ELSE 'fi_manager'::userrole
        END
    """)
    op.execute("DROP TYPE userrole_new")

    # Remove is_verified column
    op.drop_column("users", "is_verified")

    # Merge first_name and last_name back to full_name
    op.drop_column("users", "last_name")
    op.alter_column("users", "first_name", new_column_name="full_name")
    op.alter_column(
        "users",
        "full_name",
        type_=sa.String(255),
        nullable=True,
        existing_type=sa.String(100),
        existing_nullable=False,
    )
