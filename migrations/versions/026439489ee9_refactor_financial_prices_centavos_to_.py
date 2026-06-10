"""refactor_financial_prices_centavos_to_pesos

Revision ID: 026439489ee9
Revises: 182e524cbfbe
Create Date: 2026-06-10 10:09:37.326355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '026439489ee9'
down_revision: Union[str, None] = '182e524cbfbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE flight_seat_pricing SET price = price / 100")
    op.execute("UPDATE bookings SET total_price = total_price / 100")


def downgrade() -> None:
    op.execute("UPDATE flight_seat_pricing SET price = price * 100")
    op.execute("UPDATE bookings SET total_price = total_price * 100")