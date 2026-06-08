"""seed_all_data

Revision ID: 32fabe6e18ec
Revises: 275eaf94fb52
Create Date: 2026-06-08 11:45:36.524857

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid

revision: str = '32fabe6e18ec'
down_revision: Union[str, None] = '275eaf94fb52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- Generate all UUIDs upfront ---
admin_id        = str(uuid.uuid4())
passenger_id    = str(uuid.uuid4())

flight_1_id     = str(uuid.uuid4())
flight_2_id     = str(uuid.uuid4())
flight_3_id     = str(uuid.uuid4())
flight_4_id     = str(uuid.uuid4())
flight_5_id     = str(uuid.uuid4())

booking_1_id    = str(uuid.uuid4())
booking_2_id    = str(uuid.uuid4())
booking_3_id    = str(uuid.uuid4())
booking_4_id    = str(uuid.uuid4())
booking_5_id    = str(uuid.uuid4())

promo_1_id      = str(uuid.uuid4())
promo_2_id      = str(uuid.uuid4())
promo_3_id      = str(uuid.uuid4())

b6  = str(uuid.uuid4()); b7  = str(uuid.uuid4()); b8  = str(uuid.uuid4())
b9  = str(uuid.uuid4()); b10 = str(uuid.uuid4()); b11 = str(uuid.uuid4())
b12 = str(uuid.uuid4()); b13 = str(uuid.uuid4()); b14 = str(uuid.uuid4())
b15 = str(uuid.uuid4()); b16 = str(uuid.uuid4()); b17 = str(uuid.uuid4())
b18 = str(uuid.uuid4()); b19 = str(uuid.uuid4()); b20 = str(uuid.uuid4())
p2  = str(uuid.uuid4()); p3  = str(uuid.uuid4())


def upgrade() -> None:
    # --- Roles ---
    op.execute("""
        INSERT INTO roles (id, name) VALUES
        (1, 'admin'),
        (2, 'passenger')
        ON CONFLICT DO NOTHING;
    """)

    # --- Seat Classes ---
    op.execute("""
        INSERT INTO seat_classes (id, name) VALUES
        (1, 'economy'),
        (2, 'business')
        ON CONFLICT DO NOTHING;
    """)

    # --- Airports ---
    op.execute("""
        INSERT INTO airports (iata_code, name, city, country, timezone, about, highlights, best_time, image_url) VALUES
        ('MNL', 'Ninoy Aquino International Airport', 'Metro Manila', 'Philippines', 'Asia/Manila',
         'Manila is the bustling capital of the Philippines, serving as the main gateway to the archipelago with world-class connections across Asia and beyond.',
         ARRAY['Intramuros', 'Rizal Park', 'BGC', 'Manila Bay Sunset'],
         'November to February',
         'https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=1200'),
        ('CEB', 'Mactan-Cebu International Airport', 'Cebu', 'Philippines', 'Asia/Manila',
         'Known as the Queen City of the South, Cebu blends beaches, heritage landmarks, and a lively food scene in one easy island escape.',
         ARRAY['Magellan''s Cross', 'Osmeña Peak', 'Kawasan Falls', 'Sinulog Festival'],
         'November to May',
         'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1200'),
        ('DVO', 'Francisco Bangoy International Airport', 'Davao', 'Philippines', 'Asia/Manila',
         'Davao offers mountain views, city comforts, and quick access to nature attractions across Mindanao.',
         ARRAY['Mount Apo', 'Philippine Eagle Center', 'People''s Park', 'Davao Crocodile Park'],
         'December to May',
         'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200'),
        ('ILO', 'Iloilo International Airport', 'Iloilo', 'Philippines', 'Asia/Manila',
         'Iloilo is the heart of Western Visayas, known for its heritage architecture, festivals, and fresh seafood.',
         ARRAY['Miagao Church', 'Dinagyang Festival', 'Iloilo River Esplanade', 'La Paz Batchoy'],
         'November to May',
         'https://images.unsplash.com/photo-1519451241324-20b4ea2c4220?w=1200'),
        ('BCD', 'Bacolod-Silay International Airport', 'Bacolod', 'Philippines', 'Asia/Manila',
         'Bacolod is the City of Smiles, known for its MassKara Festival, heritage sites, and sweet delicacies.',
         ARRAY['MassKara Festival', 'The Ruins', 'Bacolod Public Plaza', 'Masskara Street Dance'],
         'October to May',
         'https://images.unsplash.com/photo-1519451241324-20b4ea2c4220?w=1200'),
        ('PPS', 'Puerto Princesa International Airport', 'Puerto Princesa', 'Philippines', 'Asia/Manila',
         'Puerto Princesa is the gateway to Palawan''s lagoons, limestone cliffs, and calm island-hopping days.',
         ARRAY['Underground River', 'Honda Bay', 'Baywalk', 'Island Hopping'],
         'November to May',
         'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1200'),
        ('KLO', 'Kalibo International Airport', 'Kalibo', 'Philippines', 'Asia/Manila',
         'Kalibo opens the door to Boracay''s powdery beaches and sunset trips across the islands of Aklan.',
         ARRAY['White Beach', 'Puka Shell Beach', 'Sunset Sailings', 'Island Hopping'],
         'December to May',
         'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=1200')
        ON CONFLICT DO NOTHING;
    """)

    # --- Aircraft ---
    op.execute("""
        INSERT INTO aircraft (id, model, total_seats, registration) VALUES
        (1, 'Airbus A320', 180, 'RP-C1234'),
        (2, 'Boeing 737-800', 160, 'RP-C5678')
        ON CONFLICT DO NOTHING;
    """)

    # --- Aircraft Seats ---
    op.execute("""
        INSERT INTO aircraft_seats (aircraft_id, seat_class_id, seat_number)
        SELECT 1, 2, 'A' || s FROM generate_series(1, 20) s
        ON CONFLICT DO NOTHING;
    """)
    op.execute("""
        INSERT INTO aircraft_seats (aircraft_id, seat_class_id, seat_number)
        SELECT 1, 1, 'B' || s FROM generate_series(1, 160) s
        ON CONFLICT DO NOTHING;
    """)
    op.execute("""
        INSERT INTO aircraft_seats (aircraft_id, seat_class_id, seat_number)
        SELECT 2, 2, 'A' || s FROM generate_series(1, 16) s
        ON CONFLICT DO NOTHING;
    """)
    op.execute("""
        INSERT INTO aircraft_seats (aircraft_id, seat_class_id, seat_number)
        SELECT 2, 1, 'B' || s FROM generate_series(1, 144) s
        ON CONFLICT DO NOTHING;
    """)

    # --- Users ---
    op.execute(f"""
        INSERT INTO users (id, role_id, first_name, last_name, email, password_hash, is_active, is_verified) VALUES
        ('{admin_id}',     1, 'Seed', 'Admin',     'seed.admin@gmail.com',
         '$2b$12$WI/lgSzb7edIPArSOQpM8.xO14DA47AyEMB4WxpPQCn9h0hrZZKk.', true, true),
        ('{passenger_id}', 2, 'Seed', 'Passenger', 'seed.passenger@gmail.com',
         '$2b$12$WI/lgSzb7edIPArSOQpM8.xO14DA47AyEMB4WxpPQCn9h0hrZZKk.', true, true)
        ON CONFLICT DO NOTHING;
    """)

    op.execute(f"""
        INSERT INTO users (id, role_id, first_name, last_name, email, password_hash, is_active, is_verified, created_at) VALUES
        ('{p2}', 2, 'Maria', 'Santos',  'maria.santos@gmail.com',  '$2b$12$WI/lgSzb7edIPArSOQpM8.xO14DA47AyEMB4WxpPQCn9h0hrZZKk.', true, true, '2026-02-10 09:00:00+00'),
        ('{p3}', 2, 'Carlo', 'Mendoza', 'carlo.mendoza@gmail.com', '$2b$12$WI/lgSzb7edIPArSOQpM8.xO14DA47AyEMB4WxpPQCn9h0hrZZKk.', true, true, '2026-04-05 10:00:00+00')
        ON CONFLICT DO NOTHING;
    """)

    # --- Flights ---
    op.execute(f"""
        INSERT INTO flights (id, flight_number, aircraft_id, origin_airport_id, destination_airport_id, departure_time, arrival_time, status, created_by) VALUES
        ('{flight_1_id}', 'SK101', 1,
            (SELECT id FROM airports WHERE iata_code='MNL'),
            (SELECT id FROM airports WHERE iata_code='CEB'),
            '2026-07-01 06:00:00+00', '2026-07-01 07:20:00+00', 'scheduled', '{admin_id}'),
        ('{flight_2_id}', 'SK102', 2,
            (SELECT id FROM airports WHERE iata_code='CEB'),
            (SELECT id FROM airports WHERE iata_code='MNL'),
            '2026-07-01 09:00:00+00', '2026-07-01 10:20:00+00', 'scheduled', '{admin_id}'),
        ('{flight_3_id}', 'SK201', 1,
            (SELECT id FROM airports WHERE iata_code='MNL'),
            (SELECT id FROM airports WHERE iata_code='DVO'),
            '2026-07-02 08:00:00+00', '2026-07-02 09:45:00+00', 'scheduled', '{admin_id}'),
        ('{flight_4_id}', 'SK301', 2,
            (SELECT id FROM airports WHERE iata_code='MNL'),
            (SELECT id FROM airports WHERE iata_code='ILO'),
            '2026-07-03 07:00:00+00', '2026-07-03 08:15:00+00', 'scheduled', '{admin_id}'),
        ('{flight_5_id}', 'SK401', 1,
            (SELECT id FROM airports WHERE iata_code='DVO'),
            (SELECT id FROM airports WHERE iata_code='MNL'),
            '2026-07-04 14:00:00+00', '2026-07-04 15:45:00+00', 'scheduled', '{admin_id}')
        ON CONFLICT DO NOTHING;
    """)

    # --- Flight Seat Pricing ---
    op.execute(f"""
        INSERT INTO flight_seat_pricing (flight_id, seat_class_id, total_seats, available_seats, price) VALUES
        ('{flight_1_id}', 1, 160, 158, 189900),
        ('{flight_1_id}', 2, 20,  18,  599900),
        ('{flight_2_id}', 1, 144, 142, 189900),
        ('{flight_2_id}', 2, 16,  14,  599900),
        ('{flight_3_id}', 1, 160, 155, 229900),
        ('{flight_3_id}', 2, 20,  19,  699900),
        ('{flight_4_id}', 1, 144, 140, 199900),
        ('{flight_4_id}', 2, 16,  15,  649900),
        ('{flight_5_id}', 1, 160, 157, 219900),
        ('{flight_5_id}', 2, 20,  20,  679900)
        ON CONFLICT DO NOTHING;
    """)
    

    # --- Bookings (Jan–Jun 2026, spread across routes) ---
    op.execute(f"""
        INSERT INTO bookings (id, user_id, flight_id, seat_class_id, seat_number, status, total_price, booked_at) VALUES
        -- January
        ('{booking_1_id}', '{passenger_id}', '{flight_1_id}', 1, 'B1',  'confirmed', 189900, '2026-01-05 08:00:00+00'),
        ('{booking_2_id}', '{passenger_id}', '{flight_3_id}', 2, 'A1',  'confirmed', 699900, '2026-01-12 09:00:00+00'),
        ('{booking_3_id}', '{p2}',           '{flight_4_id}', 1, 'B5',  'confirmed', 199900, '2026-01-20 10:00:00+00'),
        -- February
        ('{booking_4_id}', '{passenger_id}', '{flight_2_id}', 1, 'B2',  'cancelled', 189900, '2026-02-03 07:00:00+00'),
        ('{booking_5_id}', '{p2}',           '{flight_5_id}', 2, 'A2',  'confirmed', 679900, '2026-02-14 11:00:00+00'),
        ('{b6}',           '{p3}',           '{flight_1_id}', 2, 'A3',  'confirmed', 599900, '2026-02-22 08:30:00+00'),
        -- March
        ('{b7}',           '{passenger_id}', '{flight_3_id}', 1, 'B8',  'confirmed', 229900, '2026-03-01 09:00:00+00'),
        ('{b8}',           '{p2}',           '{flight_4_id}', 2, 'A4',  'confirmed', 649900, '2026-03-10 14:00:00+00'),
        ('{b9}',           '{p3}',           '{flight_2_id}', 1, 'B10', 'cancelled', 189900, '2026-03-18 07:30:00+00'),
        ('{b10}',          '{passenger_id}', '{flight_5_id}', 1, 'B12', 'confirmed', 219900, '2026-03-25 10:00:00+00'),
        -- April
        ('{b11}',          '{p2}',           '{flight_1_id}', 1, 'B15', 'confirmed', 189900, '2026-04-02 08:00:00+00'),
        ('{b12}',          '{p3}',           '{flight_3_id}', 2, 'A5',  'confirmed', 699900, '2026-04-08 09:30:00+00'),
        ('{b13}',          '{passenger_id}', '{flight_4_id}', 1, 'B18', 'cancelled', 199900, '2026-04-15 11:00:00+00'),
        ('{b14}',          '{p2}',           '{flight_2_id}', 2, 'A6',  'confirmed', 599900, '2026-04-22 14:00:00+00'),
        ('{b15}',          '{p3}',           '{flight_5_id}', 1, 'B20', 'confirmed', 219900, '2026-04-28 07:00:00+00'),
        -- May
        ('{b16}',          '{passenger_id}', '{flight_1_id}', 2, 'A7',  'confirmed', 599900, '2026-05-05 08:00:00+00'),
        ('{b17}',          '{p2}',           '{flight_3_id}', 1, 'B22', 'confirmed', 229900, '2026-05-12 09:00:00+00'),
        ('{b18}',          '{p3}',           '{flight_4_id}', 2, 'A8',  'cancelled', 649900, '2026-05-20 10:30:00+00'),
        ('{b19}',          '{passenger_id}', '{flight_2_id}', 1, 'B25', 'confirmed', 189900, '2026-05-27 14:00:00+00'),
        -- June
        ('{b20}',          '{p2}',           '{flight_5_id}', 2, 'A9',  'confirmed', 679900, '2026-06-03 08:00:00+00')
        ON CONFLICT DO NOTHING;
    """)


    # --- Passengers ---
    op.execute(f"""
        INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality) VALUES
        ('{booking_1_id}', 'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{booking_2_id}', 'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{booking_3_id}', 'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{booking_4_id}', 'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{booking_5_id}', 'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{b6}',           'Carlo',   'Mendoza',   '1985-06-18', 'P4567890E', 'Filipino'),
        ('{b7}',           'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{b8}',           'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{b9}',           'Carlo',   'Mendoza',   '1985-06-18', 'P4567890E', 'Filipino'),
        ('{b10}',          'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{b11}',          'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{b12}',          'Carlo',   'Mendoza',   '1985-06-18', 'P4567890E', 'Filipino'),
        ('{b13}',          'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{b14}',          'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{b15}',          'Carlo',   'Mendoza',   '1985-06-18', 'P4567890E', 'Filipino'),
        ('{b16}',          'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{b17}',          'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino'),
        ('{b18}',          'Carlo',   'Mendoza',   '1985-06-18', 'P4567890E', 'Filipino'),
        ('{b19}',          'Juan',    'Dela Cruz', '1990-03-15', 'P1234567A', 'Filipino'),
        ('{b20}',          'Maria',   'Santos',    '1995-07-22', 'P7654321B', 'Filipino')
        ON CONFLICT DO NOTHING;
    """)

    

    # --- Cancellations ---
    op.execute(f"""
        INSERT INTO cancellations (booking_id, cancelled_by, reason, refund_amount, cancelled_at) VALUES
        ('{booking_4_id}', '{passenger_id}', 'Change of plans',     189900, '2026-02-03 08:00:00+00'),
        ('{b9}',           '{p3}',           'Schedule conflict',   189900, '2026-03-18 08:00:00+00'),
        ('{b13}',          '{passenger_id}', 'Medical emergency',   199900, '2026-04-15 12:00:00+00'),
        ('{b18}',          '{p3}',           'Flight rescheduled',  649900, '2026-05-20 11:00:00+00')
        ON CONFLICT DO NOTHING;
    """)


    # --- Reschedule History ---
    op.execute(f"""
        INSERT INTO reschedule_history (booking_id, old_flight_id, new_flight_id, rescheduled_by, reason, rescheduled_at) VALUES
        ('{booking_2_id}', '{flight_2_id}', '{flight_3_id}', '{passenger_id}', 'Earlier flight preferred', '2026-01-12 10:00:00+00'),
        ('{b7}',           '{flight_1_id}', '{flight_3_id}', '{passenger_id}', 'Better route',             '2026-03-01 10:00:00+00')
        ON CONFLICT DO NOTHING;
    """)

    # --- Promotions ---
    op.execute(f"""
        INSERT INTO promotions (id, title, sale_price, original_price, discount_text, badge_text, badge_type, valid_until, image_url, destination_city, destination_code) VALUES
        ('{promo_1_id}', 'Cebu Summer Getaway',  1899.00, 3500.00, '46% OFF', 'HOT DEAL', 'hot',     '2026-08-31', 'https://images.unsplash.com/photo-1518509562904-e7ef99cdcc86?w=800', 'Cebu',   'CEB'),
        ('{promo_2_id}', 'Davao Adventure',      2299.00, 4000.00, '43% OFF', 'LIMITED',  'limited', '2026-07-31', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=800', 'Davao',  'DVO'),
        ('{promo_3_id}', 'Iloilo Heritage Tour', 1999.00, 3200.00, '38% OFF', 'NEW',      'new',     '2026-09-30', 'https://images.unsplash.com/photo-1519451241324-20b4ea2c4220?w=800', 'Iloilo', 'ILO')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM reschedule_history")
    op.execute("DELETE FROM cancellations")
    op.execute("DELETE FROM passengers")
    op.execute("DELETE FROM bookings")
    op.execute("DELETE FROM flight_seat_pricing")
    op.execute("DELETE FROM flights")
    op.execute("DELETE FROM promotions")
    op.execute("DELETE FROM users")
    op.execute("DELETE FROM aircraft_seats")
    op.execute("DELETE FROM aircraft")
    op.execute("DELETE FROM airports")
    op.execute("DELETE FROM seat_classes")
    op.execute("DELETE FROM roles")
    op.execute("ALTER SEQUENCE aircraft_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE aircraft_seats_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE airports_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE seat_classes_id_seq RESTART WITH 1")
    op.execute("ALTER SEQUENCE roles_id_seq RESTART WITH 1")