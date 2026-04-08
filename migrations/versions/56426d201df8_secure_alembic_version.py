"""secure alembic_version

Revision ID: 56426d201df8
Revises: f5d1afa4b316
Create Date: 2026-04-08 15:20:43.346351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56426d201df8'
down_revision: Union[str, None] = 'f5d1afa4b316'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op

def upgrade():
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;")

def downgrade():
    op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY;")
