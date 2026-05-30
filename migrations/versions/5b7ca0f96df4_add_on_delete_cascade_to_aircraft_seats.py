"""add_on_delete_cascade_to_aircraft_seats

Revision ID: 5b7ca0f96df4
Revises: 92250dc (or check latest)
Create Date: 2026-05-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5b7ca0f96df4'
down_revision: Union[str, None] = '8e73ea251568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Drop existing FK
    op.drop_constraint('aircraft_seats_aircraft_id_fkey', 'aircraft_seats', type_='foreignkey')
    # Re-add with CASCADE
    op.create_foreign_key(
        'aircraft_seats_aircraft_id_fkey',
        'aircraft_seats', 'aircraft',
        ['aircraft_id'], ['id'],
        ondelete='CASCADE'
    )

def downgrade() -> None:
    op.drop_constraint('aircraft_seats_aircraft_id_fkey', 'aircraft_seats', type_='foreignkey')
    op.create_foreign_key(
        'aircraft_seats_aircraft_id_fkey',
        'aircraft_seats', 'aircraft',
        ['aircraft_id'], ['id']
    )
