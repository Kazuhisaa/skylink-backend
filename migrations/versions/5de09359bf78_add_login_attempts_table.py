"""add login_attempts table
Revision ID: 5de09359bf78
Revises: 68690432fba4
Create Date: 2026-04-13 12:54:51.360912
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '5de09359bf78'
down_revision: Union[str, None] = '68690432fba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_attempts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('attempted_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_login_attempts_email', 'login_attempts', ['email'])
    op.create_index('ix_login_attempts_attempted_at', 'login_attempts', ['attempted_at'])

    # RLS
    op.execute("ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY "No public access to login_attempts"
        ON public.login_attempts
        FOR ALL
        USING (false);
    """)


def downgrade() -> None:
    op.execute('DROP POLICY IF EXISTS "No public access to login_attempts" ON public.login_attempts;')
    op.drop_index('ix_login_attempts_attempted_at', table_name='login_attempts')
    op.drop_index('ix_login_attempts_email', table_name='login_attempts')
    op.drop_table('login_attempts')