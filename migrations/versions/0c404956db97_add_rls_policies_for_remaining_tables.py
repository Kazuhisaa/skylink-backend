"""add rls policies for remaining tables

Revision ID: 0c404956db97
Revises: 56426d201df8
Create Date: 2026-04-08 15:45:07.912638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c404956db97'
down_revision: Union[str, None] = '56426d201df8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # These tables are internal/lookup — allow read for authenticated users
    for table in ["aircraft", "seat_classes", "flight_seat_pricing", "roles"]:
        op.execute(f"""
            CREATE POLICY "Authenticated users can read {table}"
            ON public.{table}
            FOR SELECT
            USING (auth.role() = 'authenticated');
        """)

    # These are user-scoped tables
    op.execute("""
        CREATE POLICY "Users can view own passengers"
        ON public.passengers
        FOR SELECT
        USING (
            booking_id IN (
                SELECT id FROM public.bookings WHERE user_id = auth.uid()
            )
        );
    """)

    op.execute("""
        CREATE POLICY "Users can view own payments"
        ON public.payments
        FOR SELECT
        USING (
            booking_id IN (
                SELECT id FROM public.bookings WHERE user_id = auth.uid()
            )
        );
    """)

    op.execute("""
        CREATE POLICY "Users can view own reschedule history"
        ON public.reschedule_history
        FOR SELECT
        USING (
            booking_id IN (
                SELECT id FROM public.bookings WHERE user_id = auth.uid()
            )
        );
    """)

    # alembic_version should NOT be publicly accessible
    op.execute("""
        CREATE POLICY "No public access to alembic_version"
        ON public.alembic_version
        FOR ALL
        USING (false);
    """)

def downgrade():
    for table in ["aircraft", "seat_classes", "flight_seat_pricing", "roles"]:
        op.execute(f'DROP POLICY IF EXISTS "Authenticated users can read {table}" ON public.{table};')

    op.execute('DROP POLICY IF EXISTS "Users can view own passengers" ON public.passengers;')
    op.execute('DROP POLICY IF EXISTS "Users can view own payments" ON public.payments;')
    op.execute('DROP POLICY IF EXISTS "Users can view own reschedule history" ON public.reschedule_history;')
    op.execute('DROP POLICY IF EXISTS "No public access to alembic_version" ON public.alembic_version;')