"""add email verification fields to user model

Revision ID: a1b2c3d4e5f6
Revises: 5de09359bf78
Create Date: 2026-04-21 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5de09359bf78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.create_index('ix_users_verification_token', 'users', ['verification_token'])


def downgrade() -> None:
    op.drop_index('ix_users_verification_token', table_name='users')
    op.drop_column('users', 'verification_token_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
