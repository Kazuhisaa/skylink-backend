"""add rls policies

Revision ID: 5d512751533a
Revises: 888607c6d054
Create Date: 2026-04-08 15:16:55.276270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d512751533a'
down_revision: Union[str, None] = '888607c6d054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.passengers ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;")

    op.execute("""
    CREATE POLICY "Users can view own profile"
    ON public.users
    FOR SELECT
    USING (auth.uid() = id);
    """)

    op.execute("""
    CREATE POLICY "Users can view own bookings"
    ON public.bookings
    FOR SELECT
    USING (auth.uid() = user_id);
    """)

def downgrade():
    op.execute('DROP POLICY IF EXISTS "Users can view own profile" ON public.users;')
    op.execute('DROP POLICY IF EXISTS "Users can view own bookings" ON public.bookings;')

    op.execute("ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.bookings DISABLE ROW LEVEL SECURITY;")