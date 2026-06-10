from pydantic import BaseModel


class KPIRead(BaseModel):
    total_flights: int
    total_bookings: int
    total_users: int
    total_revenue: float
    flights_change: float
    bookings_change: float
    users_change: float
    revenue_change: float
