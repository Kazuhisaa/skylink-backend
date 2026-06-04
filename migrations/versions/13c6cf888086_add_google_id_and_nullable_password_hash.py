"""add_google_id_and_nullable_password_hash

Revision ID: 13c6cf888086
Revises: 1010d896c98c
Create Date: 2026-06-04 17:54:05.535085

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13c6cf888086'
down_revision: Union[str, None] = '5b7ca0f96df4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    op.alter_column('users', 'password_hash',
        existing_type=sa.String(255),
        nullable=True
    )

def downgrade() -> None:
    op.alter_column('users', 'password_hash',
        existing_type=sa.String(255),
        nullable=False
    )
    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_column('users', 'google_id')
