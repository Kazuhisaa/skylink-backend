BEGIN;

-- BOOKINGS (must be first)
INSERT INTO bookings (id, user_id, flight_id, seat_class_id, seat_number, status, total_price) VALUES
(gen_random_uuid(), '5a8af260-4b80-4711-84ac-20da173b07f8', '9c018ec0-6ea0-42c0-8401-b9a825b3883b', 1, '12A', 'confirmed', 299900),
(gen_random_uuid(), '5a8af260-4b80-4711-84ac-20da173b07f8', '254c3f41-da6c-44fb-81ce-f9a9f8c1c93c', 2, '2B', 'confirmed', 899900),
(gen_random_uuid(), '5a8af260-4b80-4711-84ac-20da173b07f8', 'bcd8a24c-0201-4886-9707-67ff5f8b1358', 1, '8C', 'cancelled', 299900),
(gen_random_uuid(), '44f80d58-244f-4888-ab02-4fcc1725f522', '136356e0-6700-499d-afb5-94fa54bb93d2', 1, '15D', 'confirmed', 299900),
(gen_random_uuid(), '44f80d58-244f-4888-ab02-4fcc1725f522', '3a0ecf8e-2ce0-4e60-a73c-4c3cb9b34ca8', 2, '1A', 'confirmed', 899900);


-- PASSENGERS (depends on bookings)
INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
SELECT id, 'John', 'Doe', '1995-03-15', 'PH123456', 'Filipino'
FROM bookings WHERE seat_number = '12A';

INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
SELECT id, 'John', 'Doe', '1995-03-15', 'PH123456', 'Filipino'
FROM bookings WHERE seat_number = '2B';

INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
SELECT id, 'John', 'Doe', '1995-03-15', 'PH123456', 'Filipino'
FROM bookings WHERE seat_number = '8C';

INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
SELECT id, 'Joe', 'Schmoe', '1990-07-22', 'PH789012', 'Filipino'
FROM bookings WHERE seat_number = '15D';

INSERT INTO passengers (booking_id, first_name, last_name, date_of_birth, passport_number, nationality)
SELECT id, 'Joe', 'Schmoe', '1990-07-22', 'PH789012', 'Filipino'
FROM bookings WHERE seat_number = '1A';


-- PAYMENTS (depends on bookings)
INSERT INTO payments (id, booking_id, amount, currency, method, status, gateway_ref, paid_at)
SELECT gen_random_uuid(), b.id, b.total_price, 'PHP', 'gcash', 'paid', 'GCX-' || substring(b.id::text, 1, 8), now()
FROM bookings b WHERE b.status = 'confirmed';


-- OPTIONAL VERIFICATION QUERIES
SELECT b.seat_number, p.first_name, p.last_name
FROM passengers p
JOIN bookings b ON b.id = p.booking_id;

SELECT b.seat_number, pay.amount, pay.status, pay.method
FROM payments pay
JOIN bookings b ON b.id = pay.booking_id;

SELECT b.id, u.email, f.flight_number, b.seat_number, b.status, b.total_price
FROM bookings b
JOIN users u ON u.id = b.user_id
JOIN flights f ON f.id = b.flight_id
ORDER BY b.booked_at;


COMMIT;