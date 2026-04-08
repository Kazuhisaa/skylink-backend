"""enable rls for remaining tables

Revision ID: f5d1afa4b316
Revises: 5d512751533a
Create Date: 2026-04-08 15:18:40.840185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5d1afa4b316'
down_revision: Union[str, None] = '5d512751533a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("ALTER TABLE public.flights ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.airports ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.aircraft ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.seat_classes ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.flight_seat_pricing ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.cancellations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.reschedule_history ENABLE ROW LEVEL SECURITY;")

    # Optional: allow public read for reference tables
    op.execute("""
    CREATE POLICY "Public read airports"
    ON public.airports
    FOR SELECT
    USING (true);
    """)

    op.execute("""
    CREATE POLICY "Public read flights"
    ON public.flights
    FOR SELECT
    USING (true);
    """)

def downgrade():
    op.execute("ALTER TABLE public.flights DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.airports DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.aircraft DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.roles DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.seat_classes DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.flight_seat_pricing DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.cancellations DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.reschedule_history DISABLE ROW LEVEL SECURITY;")