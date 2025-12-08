"""add wallet and transaction models with permissions

Revision ID: b93f428e9c71
Revises: 817f987f51f0
Create Date: 2025-12-08 23:10:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = "b93f428e9c71"
down_revision = "817f987f51f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add google_id to users table
    op.add_column("users", sa.Column("google_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)

    # Make hashed_password nullable for Google OAuth users
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=True
    )

    # Add permissions column to api_keys table
    op.add_column(
        "api_keys",
        sa.Column(
            "permissions", sa.String(), nullable=False, server_default='["read"]'
        ),
    )

    # Create wallets table
    op.create_table(
        "wallets",
        sa.Column("id", sa.Uuid(), nullable=False, default=uuid.uuid4),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("wallet_number", sa.String(length=13), nullable=False),
        sa.Column(
            "balance",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wallets_id"), "wallets", ["id"], unique=False)
    op.create_index(op.f("ix_wallets_user_id"), "wallets", ["user_id"], unique=True)
    op.create_index(
        op.f("ix_wallets_wallet_number"), "wallets", ["wallet_number"], unique=True
    )

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False, default=uuid.uuid4),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("wallet_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("deposit", "transfer_in", "transfer_out", name="transactiontype"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "success", "failed", name="transactionstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("metadata", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["wallets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_transactions_id"), "transactions", ["id"], unique=False)
    op.create_index(
        op.f("ix_transactions_reference"), "transactions", ["reference"], unique=True
    )
    op.create_index(
        op.f("ix_transactions_wallet_id"), "transactions", ["wallet_id"], unique=False
    )


def downgrade() -> None:
    # Drop transactions table
    op.drop_index(op.f("ix_transactions_wallet_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_reference"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_id"), table_name="transactions")
    op.drop_table("transactions")

    # Drop wallets table
    op.drop_index(op.f("ix_wallets_wallet_number"), table_name="wallets")
    op.drop_index(op.f("ix_wallets_user_id"), table_name="wallets")
    op.drop_index(op.f("ix_wallets_id"), table_name="wallets")
    op.drop_table("wallets")

    # Remove permissions column from api_keys
    op.drop_column("api_keys", "permissions")

    # Revert hashed_password to not nullable
    op.alter_column(
        "users", "hashed_password", existing_type=sa.String(), nullable=False
    )

    # Remove google_id from users
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    op.drop_column("users", "google_id")
