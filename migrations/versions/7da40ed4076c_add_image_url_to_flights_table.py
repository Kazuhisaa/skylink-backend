"""add image_url to flights table

Revision ID: 7da40ed4076c
Revises: b2c3d4e5f6g7
Create Date: 2026-05-25 17:02:03.060969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7da40ed4076c'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('flights', sa.Column('image_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('flights', 'image_url')
