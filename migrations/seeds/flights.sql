begin;

-- Airports
INSERT INTO airports (iata_code, name, city, country, timezone) VALUES
('MNL', 'Ninoy Aquino International Airport', 'Manila', 'Philippines', 'Asia/Manila'),
('CEB', 'Mactan-Cebu International Airport', 'Cebu', 'Philippines', 'Asia/Manila'),
('DVO', 'Francisco Bangoy International Airport', 'Davao', 'Philippines', 'Asia/Manila'),
('ILO', 'Iloilo International Airport', 'Iloilo', 'Philippines', 'Asia/Manila'),
('BCD', 'Bacolod-Silay Airport', 'Bacolod', 'Philippines', 'Asia/Manila');

-- Aircraft
INSERT INTO aircraft (model, total_seats, registration) VALUES
('Airbus A320', 180, 'RP-C3200'),
('Boeing 737-800', 162, 'RP-C7380'),
('ATR 72-600', 70, 'RP-C7260');

-- Seat Classes
INSERT INTO seat_classes (name) VALUES
('economy'),
('business');

-- Flights (replace the created_by UUID with your admin UUID)
INSERT INTO flights (id, flight_number, aircraft_id, origin_airport_id, destination_airport_id, departure_time, arrival_time, status, created_by) VALUES
(gen_random_uuid(), 'SK101', 1, 1, 2, '2026-05-01 06:00:00+00', '2026-05-01 07:30:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK102', 1, 2, 1, '2026-05-01 09:00:00+00', '2026-05-01 10:30:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK201', 2, 1, 3, '2026-05-01 08:00:00+00', '2026-05-01 09:45:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK202', 2, 3, 1, '2026-05-01 11:00:00+00', '2026-05-01 12:45:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK301', 3, 1, 4, '2026-05-01 07:00:00+00', '2026-05-01 08:15:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK302', 3, 4, 1, '2026-05-01 10:00:00+00', '2026-05-01 11:15:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a'),
(gen_random_uuid(), 'SK401', 3, 1, 5, '2026-05-02 06:30:00+00', '2026-05-02 07:45:00+00', 'scheduled', '80376e15-df8f-42cf-8472-ed7b6fb8248a');

-- Flight Seat Pricing
INSERT INTO flight_seat_pricing (flight_id, seat_class_id, total_seats, available_seats, price)
SELECT f.id, 1, (a.total_seats * 0.85)::int, (a.total_seats * 0.85)::int, 299900
FROM flights f JOIN aircraft a ON f.aircraft_id = a.id;

INSERT INTO flight_seat_pricing (flight_id, seat_class_id, total_seats, available_seats, price)
SELECT f.id, 2, (a.total_seats * 0.15)::int, (a.total_seats * 0.15)::int, 899900
FROM flights f JOIN aircraft a ON f.aircraft_id = a.id;

-- OPTIONAL VERIFICATION QUERIES
SELECT f.flight_number, sc.name, fsp.total_seats, fsp.available_seats, fsp.price
FROM flight_seat_pricing fsp
JOIN flights f ON f.id = fsp.flight_id
JOIN seat_classes sc ON sc.id = fsp.seat_class_id
ORDER BY f.flight_number, sc.name;

commit;





