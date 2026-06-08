"""fix rls policies idempotent

Revision ID: 275eaf94fb52
Revises: 818e0c4fc5c3
Create Date: 2026-06-08 11:19:36.194932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '275eaf94fb52'
down_revision: Union[str, None] = '818e0c4fc5c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS "Users can view own profile" ON public.users;

    CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);
    """)


def downgrade() -> None:
    pass
