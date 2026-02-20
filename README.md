# 🛒 Mangunas Supermarket POS System

A full-stack Point of Sale system built with **Django REST Framework** + **React**, featuring **M-Pesa STK Push** payment integration (Safaricom Daraja API), JWT authentication, inventory management, and a clean dark-themed UI.

---

## 📁 Project Structure

```
mangunas_pos/
├── backend/                        # Django project
│   ├── mangunas_pos/               # Django project config
│   │   ├── __init__.py
│   │   ├── settings.py             # All project settings
│   │   ├── urls.py                 # Root URL config
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── pos/                        # Main POS app
│   │   ├── migrations/             # Database migrations
│   │   ├── __init__.py
│   │   ├── admin.py                # Django admin configuration
│   │   ├── apps.py
│   │   ├── models.py               # All data models
│   │   ├── serializers.py          # DRF serializers
│   │   ├── views.py                # ViewSets + API views
│   │   └── urls.py                 # App URL patterns
│   ├── media/                      # Uploaded product images
│   ├── staticfiles/                # Collected static files
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variable template
│   └── manage.py
│
└── frontend/                       # React + Vite project
    ├── public/
    ├── src/
    │   ├── App.jsx                 # All pages + routing (single-file)
    │   ├── index.css               # Full design system CSS
    │   └── main.jsx                # React entry point
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## 🗄️ Django Models

| Model | Purpose |
|-------|---------|
| `Category` | Product categories (Beverages, Dairy, etc.) |
| `Product` | Items with barcode, price, cost, stock qty |
| `Customer` | Customer profiles with loyalty points |
| `Order` | Sales orders with auto-generated order numbers |
| `OrderItem` | Line items within an order |
| `Payment` | Supports Cash, M-Pesa, Card; M-Pesa fields included |
| `StockMovement` | Full audit trail of all stock changes |

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Login → returns JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |

### Resources (CRUD)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/categories/` | List / Create categories |
| GET/POST | `/api/products/` | List / Create products |
| GET/POST | `/api/customers/` | List / Create customers |
| GET/POST | `/api/orders/` | List / Create orders |
| POST | `/api/orders/{id}/cancel/` | Cancel an order |
| GET | `/api/stock-movements/` | View stock audit trail |
| POST | `/api/products/adjust_stock/` | Manual stock adjustment |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/cash/` | Process cash payment |
| POST | `/api/payments/mpesa/stk-push/` | Initiate M-Pesa STK push |
| POST | `/api/payments/mpesa/callback/` | Safaricom webhook (public) |
| GET | `/api/payments/mpesa/query/{id}/` | Query STK push status |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/` | Today's stats + recent orders |

---

## ⚙️ Backend Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 14+

### 2. Install & Configure

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and M-Pesa keys
```

### 3. Database

```bash
# Create PostgreSQL database
createdb mangunas_pos

# Run migrations
python manage.py migrate

# Create superuser (for admin panel)
python manage.py createsuperuser
```

### 4. Run the Server

```bash
python manage.py runserver
```

API available at: `http://localhost:8000/api/`  
Admin panel: `http://localhost:8000/admin/`

---

## 💻 Frontend Setup

### 1. Prerequisites
- Node.js 18+

### 2. Install & Run

```bash
cd frontend

npm install
npm run dev
```

App available at: `http://localhost:5173`

---

## 📱 M-Pesa Integration

This system uses the **Safaricom Daraja API** (STK Push / Lipa Na M-Pesa Online).

### Setup Steps

1. **Register** at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. **Create an app** → get Consumer Key & Consumer Secret
3. For sandbox testing, use the provided test credentials
4. **Set your callback URL** — this must be a publicly accessible HTTPS URL (use [ngrok](https://ngrok.com) for local dev)

### .env Configuration

```env
MPESA_ENVIRONMENT=sandbox
MPESA_CONSUMER_KEY=your_consumer_key
MPESA_CONSUMER_SECRET=your_consumer_secret
MPESA_SHORTCODE=174379              # Sandbox shortcode
MPESA_PASSKEY=your_sandbox_passkey
MPESA_CALLBACK_URL=https://your-ngrok-url.ngrok.io/api/payments/mpesa/callback/
```

### Payment Flow

```
Cashier enters customer phone → POST /api/payments/mpesa/stk-push/
    ↓
Django calls Safaricom STK Push API → Customer gets prompt on phone
    ↓
Customer enters M-Pesa PIN on phone
    ↓
Safaricom calls our callback → POST /api/payments/mpesa/callback/
    ↓
Payment marked COMPLETED → Order status = completed
```

### Testing with ngrok

```bash
ngrok http 8000
# Copy the https URL and set it as MPESA_CALLBACK_URL in .env
```

---

## 🔐 Authentication

The system uses **JWT tokens** via `djangorestframework-simplejwt`:
- Access token: 8 hours
- Refresh token: 7 days

The frontend stores tokens in `localStorage` and attaches them automatically via an Axios interceptor.

---

## 🧾 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | JWT-based authentication |
| POS Terminal | `/pos` | Main sales screen with cart |
| Dashboard | `/dashboard` | Today's stats, recent orders |
| Products | `/products` | Product catalog management |
| Orders | `/orders` | Order history and detail view |
| Customers | `/customers` | Customer management |

---

## 🚀 Production Deployment

### Backend

```bash
# Collect static files
python manage.py collectstatic

# Run with gunicorn
gunicorn mangunas_pos.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Recommended: put behind Nginx
```

### Frontend

```bash
npm run build
# Deploy dist/ folder to your web server or CDN
```

### Environment Checklist for Production
- [ ] Set `DEBUG=False`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Set `CORS_ALLOWED_ORIGINS` to your frontend URL
- [ ] Switch `MPESA_ENVIRONMENT=production`
- [ ] Use real Safaricom production credentials
- [ ] Configure PostgreSQL with a strong password
- [ ] Enable HTTPS on your server

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.0, Django REST Framework |
| Auth | JWT (djangorestframework-simplejwt) |
| Database | PostgreSQL |
| Payments | Safaricom M-Pesa Daraja API |
| Frontend | React 18, Vite |
| HTTP Client | Axios |
| Routing | React Router v6 |
| Fonts | Syne + JetBrains Mono (Google Fonts) |

---

## 👨‍💻 Development Notes

- **VAT**: Set to 16% (Kenya standard rate) in `models.py → Order.calculate_totals()`
- **Currency**: Kenyan Shilling (KSh)
- **Timezone**: Africa/Nairobi in settings
- **Barcode scanning**: The product search field on POS also works with a barcode scanner (scan → lookup by barcode parameter)
- **Stock tracking**: Every sale, return, and manual adjustment creates a `StockMovement` record for full audit trail

---

*Built for Mangunas Supermarket — Kenya*