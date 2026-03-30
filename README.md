# SkyLink Airline Reservation System — Backend API

A web-based airline reservation system built with FastAPI and Supabase (PostgreSQL). This backend provides RESTful API endpoints for flight searching, ticket booking, payment processing, and admin management.

---

## Tech Stack

- **Framework:** FastAPI (Python 3.11)
- **Database:** Supabase (PostgreSQL) via SQLAlchemy
- **Authentication:** JWT (python-jose + passlib)
- **ORM:** SQLAlchemy + Alembic (migrations)
- **Server:** Uvicorn
- **Project Management:** Jira + GitHub (connected via Atlassian app)
- **CI/CD:** GitHub Actions

---

## Project Structure

```
skylink-api/
├── main.py                  # FastAPI app entry point
├── database.py              # Database connection (SQLAlchemy + Supabase)
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not committed)
├── .env.example             # Environment variable template
├── .gitignore
├── .github/
│   ├── workflows/
│   │   └── ci.yml           # GitHub Actions CI/CD pipeline
│   └── pull_request_template.md
├── app/
│   ├── routers/
│   │   ├── auth.py          # User registration and login
│   │   ├── flights.py       # Flight search and filtering
│   │   ├── bookings.py      # Ticket booking and cancellation
│   │   └── admin.py         # Admin dashboard routes
│   ├── models/
│   │   └── models.py        # SQLAlchemy database models
│   ├── schemas/
│   │   └── schemas.py       # Pydantic request/response schemas
│   └── services/
│       └── auth_service.py  # Authentication business logic
├── migrations/              # Alembic migration files
└── tests/                   # Pytest test files
```

---

## Getting Started

### Prerequisites

- Python 3.11
- Git
- Supabase account

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Kazuhisaa/skylink-backend.git
cd skylink-backend
```

2. **Create and activate virtual environment**
```bash
# Windows
py -3.11 -m venv venv
venv\Scripts\activate

# Mac/Linux
python3.11 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Copy `.env.example` to `.env` and fill in your values:
```bash
copy .env.example .env
```

`.env` contents:
```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
DATABASE_URL=postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
```

5. **Run the development server**
```bash
uvicorn main:app --reload
```

6. **Access the API docs**

Open your browser and go to:
```
http://localhost:8000/docs
```

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and get JWT token |

### Flights
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/flights` | Search and filter flights |
| GET | `/flights/{id}` | Get flight details |

### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/bookings` | Book a ticket |
| DELETE | `/bookings/{id}` | Cancel a booking |
| PUT | `/bookings/{id}` | Reschedule a booking |
| GET | `/bookings` | View booking history |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/flights` | Add a new flight |
| PUT | `/admin/flights/{id}` | Edit a flight |
| DELETE | `/admin/flights/{id}` | Delete a flight |
| GET | `/admin/users` | View all users |
| GET | `/admin/reports` | View booking reports |

---

## Git Workflow

This project follows a feature branch workflow connected to Jira:

```
main                    # Production-ready code
└── develop             # Integration branch
    └── feature/SKYLINK-{issue-number}-{description}
```

### Branch Naming Convention
```
feature/SKYLINK-6-user-registration
feature/SKYLINK-8-jwt-token
```

### Commit Message Convention
```
SKYLINK-{issue-number}: short description of change

Example:
SKYLINK-6: implement user registration endpoint
```

### Pull Request Process
1. Create a branch from `main` using the Jira issue key
2. Write code and commit with Jira issue key in the message
3. Push branch and open a Pull Request
4. GitHub Actions CI will automatically run tests
5. PR must pass all checks before merging
6. Merging PR automatically updates Jira issue to Done

---

## CI/CD Pipeline

GitHub Actions runs automatically on every push and PR:

- Install Python dependencies
- Run pytest test suite
- Check code style with flake8
- Block merge if any check fails

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase publishable key |
| `DATABASE_URL` | PostgreSQL connection string from Supabase |
| `JWT_SECRET_KEY` | Secret key for JWT token signing |
| `JWT_ALGORITHM` | JWT algorithm (default: HS256) |

> **Never commit your `.env` file.** Share credentials with teammates via private message only.


## Jira Project

Track all issues and sprint progress on our Jira board:
[SkyLink Jira Board](https://jebreilblancada.atlassian.net/jira/software/projects/SKYLINK/boards)

---

## License

For academic purposes only — SkyLink Airline Reservation System.
