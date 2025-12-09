# Wallet Service with Paystack, JWT & API Keys

A production-ready backend wallet service built with FastAPI, featuring Google OAuth authentication, API key management, Paystack payment integration, and wallet-to-wallet transfers.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)

## 🚀 Features

- **Dual Authentication**
  - Google OAuth 2.0 sign-in with JWT tokens
  - Username/password authentication (backup)
  
- **API Key Management**
  - Permission-based access (deposit, transfer, read)
  - Flexible expiry formats (1H, 1D, 1M, 1Y)
  - Maximum 5 active keys per user
  - API key rollover for expired keys

- **Wallet Operations**
  - Automatic wallet creation on user registration
  - Unique 13-digit wallet numbers
  - Real-time balance tracking
  - Transaction history with pagination

- **Paystack Integration**
  - Deposit initialization with payment links
  - **Mandatory webhook handling** for automatic crediting
  - Webhook signature validation
  - Idempotent transaction processing

- **Wallet Transfers**
  - Atomic wallet-to-wallet transfers
  - Balance validation
  - Self-transfer prevention
  - Dual transaction recording (OUT/IN)

- **Security**
  - HMAC-SHA512 webhook signature verification
  - bcrypt password hashing
  - JWT token-based authentication
  - API key permission enforcement
  - CORS configuration

## 📋 Requirements

- Python 3.12+
- PostgreSQL 14+
- Paystack account (test/live keys)
- Google OAuth credentials (optional)

## 🛠️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/Imuaz/hng-be-s8.git
cd hng-be-s8
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

**Required variables:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/wallet_db
SECRET_KEY=your-secret-key-minimum-32-characters
PAYSTACK_SECRET_KEY=sk_test_your_paystack_secret
PAYSTACK_PUBLIC_KEY=pk_test_your_paystack_public

# Optional (for Google OAuth)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### 5. Setup Database

```bash
# Create database
createdb wallet_db

# Run migrations
alembic upgrade head
```

### 6. Run Server

```bash
uvicorn main:app --reload
```

Server runs at: http://localhost:8000

API Documentation: http://localhost:8000/docs

## 📚 API Endpoints

### Authentication

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/auth/google` | Initiate Google OAuth | None |
| GET | `/auth/google/callback` | OAuth callback, returns JWT | None |
| POST | `/auth/signup` | Create account | None |
| POST | `/auth/login` | Login, returns JWT | None |

### API Keys

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/keys/create` | Create API key | JWT |
| POST | `/keys/rollover` | Rollover expired key | JWT |
| GET | `/keys` | List user's API keys | JWT |
| DELETE | `/keys/{key_id}` | Revoke API key | JWT |

### Wallet Operations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/wallet/balance` | Get wallet balance | JWT or API key (read) |
| POST | `/wallet/deposit` | Initialize Paystack deposit | JWT or API key (deposit) |
| POST | `/wallet/paystack/webhook` | Paystack webhook handler | Webhook signature |
| GET | `/wallet/deposit/{ref}/status` | Check deposit status | JWT or API key (read) |
| POST | `/wallet/transfer` | Transfer to another wallet | JWT or API key (transfer) |
| GET | `/wallet/transactions` | Transaction history | JWT or API key (read) |

## 🔐 Authentication

### Using JWT (User Authentication)

```bash
# 1. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}'

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 2. Use token
curl http://localhost:8000/wallet/balance \
  -H "Authorization: Bearer eyJ..."
```

### Using API Keys (Service Access)

```bash
# 1. Create API key
curl -X POST http://localhost:8000/keys/create \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "wallet-service",
    "permissions": ["deposit", "transfer", "read"],
    "expiry": "1M"
  }'

# Response: {"api_key": "sk_...", "expires_at": "..."}

# 2. Use API key
curl http://localhost:8000/wallet/balance \
  -H "x-api-key: sk_..."
```

## 💰 Usage Examples

### Make a Deposit

```bash
# Initialize deposit
curl -X POST http://localhost:8000/wallet/deposit \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 5000}'

# Response includes Paystack payment link
{
  "reference": "DEP-xxxxx",
  "authorization_url": "https://checkout.paystack.com/xxxxx",
  "access_code": "xxxxx"
}

# User completes payment → Paystack sends webhook → Wallet credited automatically
```

### Transfer Funds

```bash
curl -X POST http://localhost:8000/wallet/transfer \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_number": "1234567890123",
    "amount": 1000
  }'
```

### View Transaction History

```bash
curl http://localhost:8000/wallet/transactions?limit=20&offset=0 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔧 Configuration

### Paystack Webhook Setup

1. Go to [Paystack Dashboard](https://dashboard.paystack.com/settings/webhooks)
2. Set webhook URL: `https://your-domain.com/wallet/paystack/webhook`
3. Select events: **All Events** or **Successful Payment**
4. Save

**For local testing:**
- Use [ngrok](https://ngrok.com/): `ngrok http 8000`
- Update webhook to: `https://your-ngrok-url.ngrok.io/wallet/paystack/webhook`

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials
3. Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
4. Copy Client ID and Client Secret to `.env`


## 🧪 Testing

### Run Tests

```bash
pytest
```

### Manual Testing

Use Swagger UI at http://localhost:8000/docs

### Test with Paystack Test Cards

```
Card Number: 4084084084084081
CVV: 408
Expiry: Any future date
PIN: 0000
OTP: 123456
```

## 📁 Project Structure

```
hng-be-s8/
├── app/
│   ├── dependencies/     # Auth dependencies
│   ├── models/          # SQLAlchemy models
│   ├── routers/         # API endpoints
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── utils/           # Helper functions
│   ├── config.py        # Configuration
│   └── database.py      # Database setup
├── migrations/          # Alembic migrations
├── main.py             # FastAPI application
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── Procfile           # Railway/Heroku config
└── README.md          # This file
```

## 🛡️ Security Features

- ✅ Password hashing with bcrypt
- ✅ JWT token authentication
- ✅ API key permission validation
- ✅ Webhook signature verification (HMAC-SHA512)
- ✅ CORS configuration
- ✅ SQL injection protection (SQLAlchemy)
- ✅ Environment variable secrets
- ✅ Idempotent webhook processing
- ✅ Atomic database transactions

## 📝 API Key Permissions

- **read**: View balance, transactions
- **deposit**: Initialize deposits
- **transfer**: Transfer funds

## ⚙️ Technical Stack

- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy
- **Authentication**: JWT (PyJWT), OAuth (Authlib)
- **Payments**: Paystack API
- **Password Hashing**: bcrypt
- **Migrations**: Alembic
- **ASGI Server**: Uvicorn

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

**Imuaz**
- GitHub: [@Imuaz](https://github.com/Imuaz)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Paystack](https://paystack.com/) - Payment infrastructure
- [HNG Internship](https://hng.tech/) - Project requirements

## 📞 Support

For support, email me or open an issue.

---

**Built with ❤️ for HNG Internship Stage 8**
