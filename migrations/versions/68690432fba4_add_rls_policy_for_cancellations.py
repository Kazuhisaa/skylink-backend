"""add rls policy for cancellations

Revision ID: 68690432fba4
Revises: 0c404956db97
Create Date: 2026-04-08 15:46:47.736981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68690432fba4'
down_revision: Union[str, None] = '0c404956db97'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
        CREATE POLICY "Users can view own cancellations"
        ON public.cancellations
        FOR SELECT
        USING (
            booking_id IN (
                SELECT id FROM public.bookings WHERE user_id = auth.uid()
            )
        );
    """)

def downgrade():
    op.execute('DROP POLICY IF EXISTS "Users can view own cancellations" ON public.cancellations;')