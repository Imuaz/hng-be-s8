# Authentication + API Key Service

> **HNG Stage 7 - Task 3:** Mini Authentication + API Key System for Service-to-Service Access

A production-ready FastAPI application implementing **dual authentication** with JWT tokens for user access and API keys for service-to-service communication.

## 🎯 Features

-  **User Authentication**: JWT-based signup/login system
- 🔐 **API Key Management**: Create, list, and revoke API keys
- 🔄 **Dual Authentication**: Support for both JWT tokens and API keys
- 🛡️ **Secure**: Password hashing with bcrypt, JWT with expiration
- 🗄️ **PostgreSQL**: Production-ready database
- ✅ **100% Test Coverage**: Comprehensive test suite
- 📚 **Auto-generated API Docs**: Interactive Swagger UI at `/docs`

## 📋 Requirements

- Python 3.10+
- PostgreSQL database
- pip (Python package manager)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd path/to/your/project directory
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Database

Create a PostgreSQL database:

```bash
# Using psql
createdb <database name>

# Or using SQL
psql -U postgres
CREATE DATABASE <database name>;
```

### 3. Environment Configuration

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DATABASE_URL=postgresql://<db_username>:<db_password>@localhost:5432/<database_name>
SECRET_KEY=your-super-secret-key-min-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES= # set the access token expiration time in minutes
API_KEY_EXPIRE_DAYS= # set the API key expiration time in days
```

### 4. Run the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## 📖 API Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 API Endpoints

### Authentication

#### **POST** `/auth/signup`
Register a new user account.

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myusername",
    "password": "securepass123"
  }'
```

#### **POST** `/auth/login`
Login and receive a JWT access token.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myusername",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### API Key Management

#### **POST** `/keys/create`
Create a new API key (requires JWT authentication).

```bash
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Service Key",
    "expires_in_days": 365
  }'
```

Response:
```json
{
  "id": 1,
  "key": "sk_Ab3D...xyz",
  "name": "My Service Key",
  "created_at": "2025-12-05T23:00:00",
  "expires_at": "2026-12-05T23:00:00",
  "is_revoked": false
}
```

⚠️ **Important**: Save the `key` value immediately - it won't be shown again!

#### **GET** `/keys`
List all your API keys.

```bash
curl -X GET http://localhost:8000/keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### **DELETE** `/keys/{key_id}`
Revoke an API key.

```bash
curl -X DELETE http://localhost:8000/keys/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Protected Routes (Demo)

#### **GET** `/protected/user`
Accessible **only** with JWT token.

```bash
curl -X GET http://localhost:8000/protected/user \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### **GET** `/protected/service`
Accessible **only** with API key.

```bash
curl -X GET http://localhost:8000/protected/service \
  -H "x-api-key: YOUR_API_KEY"
```

#### **GET** `/protected/any`
Accessible with **either** JWT token **or** API key.

```bash
# With JWT
curl -X GET http://localhost:8000/protected/any \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# With API key
curl -X GET http://localhost:8000/protected/any \
  -H "x-api-key: YOUR_API_KEY"
```

## 🧪 Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
```

## 🏗️ Project Structure

```
hng-be-s7/
├── app/
│   ├── config.py              # Environment configuration
│   ├── database.py            # Database setup and session
│   ├── models/
│   │   └── auth.py            # SQLAlchemy models
│   ├── schemas/
│   │   └── auth.py            # Pydantic schemas
│   ├── services/
│   │   ├── auth.py            # Authentication business logic
│   │   └── api_keys.py        # API key management logic
│   ├── dependencies/
│   │   └── auth.py            # Auth dependencies
│   ├── routers/
│   │   ├── auth.py            # Auth endpoints
│   │   ├── api_keys.py        # API key endpoints
│   │   └── protected.py       # Protected demo routes
│   └── utils/
│       └── security.py        # Security utilities
├── tests/
│   ├── conftest.py            # Pytest fixtures
│   ├── test_auth.py           # Auth endpoint tests
│   ├── test_api_keys.py       # API key tests
│   └── test_protected.py      # Protected route tests
├── main.py                    # FastAPI application
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🔐 Authentication Flow

### User Authentication (JWT)
1. User signs up via `/auth/signup`
2. User logs in via `/auth/login` and receives a JWT token
3. Include token in requests: `Authorization: Bearer <token>`
4. Token expires after 30 minutes (configurable)

### Service Authentication (API Key)
1. User creates API key via `/keys/create` (requires JWT)
2. Use API key in requests: `x-api-key: <key>`
3. API key expires after 365 days (configurable)
4. Keys can be revoked anytime via `/keys/{key_id}`

## 🛡️ Security Features

- ✅ Password hashing with bcrypt
- ✅ JWT tokens with configurable expiration
- ✅ API key expiration and revocation
- ✅ Protected routes with flexible authentication
- ✅ CORS middleware configured
- ✅ Input validation with Pydantic
- ✅ SQL injection protection via SQLAlchemy ORM

## 🔧 Configuration

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | 30 |
| `API_KEY_EXPIRE_DAYS` | API key lifetime | 365 |
| `CORS_ORIGINS` | Allowed CORS origins | localhost |

## 📝 License

MIT License - feel free to use this for your projects!

## 👨‍💻 Author

- [I Muaz](https://github.com/imuaz) - Built for HNG Stage 7 Task 3

---

**Happy Coding!** 🚀
