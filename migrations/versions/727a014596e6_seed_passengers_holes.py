"""seed passengers holes

Revision ID: 727a014596e6
Revises: 5e600f53072c
Create Date: 2026-06-15 15:56:09.624533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '727a014596e6'
down_revision: Union[str, None] = '5e600f53072c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
        SELECT 
            b.id,
            'Juan',
            'Dela Cruz',
            '1990-01-01',
            NULL,
            'Filipino'
        FROM bookings b
        WHERE NOT EXISTS (
            SELECT 1 FROM passengers p WHERE p.booking_id = b.id
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM passengers
        WHERE first_name IN ('Juan', 'Maria', 'Jose', 'Ana', 'Miguel', 'Rosa', 'Carlo', 'Liza', 'Marco', 'Nina')
        AND last_name IN ('Dela Cruz', 'Santos', 'Reyes', 'Garcia', 'Torres', 'Flores', 'Rivera', 'Lopez', 'Mendoza', 'Ramos')
        AND nationality = 'Filipino'
        AND passport_number IS NULL
    """)
