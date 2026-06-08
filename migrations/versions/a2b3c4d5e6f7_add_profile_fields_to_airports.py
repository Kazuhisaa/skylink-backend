"""seed airport profiles

Revision ID: a2b3c4d5e6f7
Revises: 888607c6d054
Create Date: 2026-06-08 13:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = '888607c6d054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add missing columns first (safe if already applied in some envs)
    op.execute("""
        ALTER TABLE airports
        ADD COLUMN IF NOT EXISTS about TEXT,
        ADD COLUMN IF NOT EXISTS highlights TEXT[],
        ADD COLUMN IF NOT EXISTS best_time TEXT,
        ADD COLUMN IF NOT EXISTS image_url TEXT;
    """)

    op.execute("""
        UPDATE airports SET
            about = 'Manila is the bustling capital of the Philippines, serving as the main gateway to the archipelago with world-class connections across Asia and beyond.',
            highlights = ARRAY['Intramuros', 'Rizal Park', 'BGC', 'Manila Bay Sunset'],
            best_time = 'November to February',
            image_url = 'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=1200'
        WHERE iata_code = 'MNL';
    """)

    op.execute("""
        UPDATE airports SET
            about = 'Known as the Queen City of the South, Cebu blends beaches, heritage landmarks, and a lively food scene in one easy island escape.',
            highlights = ARRAY['Magellan''s Cross', 'Osmeña Peak', 'Kawasan Falls', 'Sinulog Festival'],
            best_time = 'November to May',
            image_url = 'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1200'
        WHERE iata_code = 'CEB';
    """)

    op.execute("""
        UPDATE airports SET
            about = 'Davao offers mountain views, city comforts, and quick access to nature attractions across Mindanao.',
            highlights = ARRAY['Mount Apo', 'Philippine Eagle Center', 'People''s Park', 'Davao Crocodile Park'],
            best_time = 'December to May',
            image_url = 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200'
        WHERE iata_code = 'DVO';
    """)

    op.execute("""
        UPDATE airports SET
            about = 'Iloilo is the heart of Western Visayas, known for its heritage architecture, festivals, and fresh seafood.',
            highlights = ARRAY['Miagao Church', 'Dinagyang Festival', 'Iloilo River Esplanade', 'La Paz Batchoy'],
            best_time = 'November to May',
            image_url = 'https://images.unsplash.com/photo-1519451241324-20b4ea2c4220?w=1200'
        WHERE iata_code = 'ILO';
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE airports
        SET about = NULL,
            highlights = NULL,
            best_time = NULL,
            image_url = NULL;
    """)