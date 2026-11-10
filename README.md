# Coderr Backend

REST API for **Coderr**, a freelancer marketplace where business users offer
services in three packages (basic, standard, premium) and customers order
them and write reviews. The backend is built with Django and Django REST
Framework and serves the separate Coderr frontend.

## Features

- Registration and login with token authentication
- Two user types: `customer` and `business`, each with its own profile
- Offers with exactly three detail packages, filtering, search, ordering and pagination
- Orders created by customers from an offer package, status managed by the business user
- Reviews: one review per customer and business user
- Public base info endpoint with platform statistics
- Guest accounts for the frontend guest login

## Tech stack

| Package | Purpose |
| ------- | ------- |
| Django 6.1 | Web framework |
| Django REST Framework 3.18 | REST API, token authentication |
| django-filter | Query parameter filters |
| django-cors-headers | CORS for the frontend |
| Pillow | Image uploads (profile pictures, offer images) |
| python-dotenv | Settings from the `.env` file |

The database is SQLite (`db.sqlite3`). It is not part of the repository and is
created by the migrations.

## Requirements

- Python **3.12 or newer** (required by Django 6.1)
- Git

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/SchumacherKevin/coderr_backend.git
   cd coderr_backend
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   ```

   | System | Activate |
   | ------ | -------- |
   | Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
   | Windows (cmd) | `.venv\Scripts\activate.bat` |
   | macOS / Linux | `source .venv/bin/activate` |

3. **Install the dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create the `.env` file**

   Copy `.env.template` to `.env` and enter your own secret key:

   ```bash
   cp .env.template .env        # Windows: copy .env.template .env
   ```

   A new key can be generated with:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   | Variable | Meaning | Default |
   | -------- | ------- | ------- |
   | `SECRET_KEY` | Django secret key, **required** | none |
   | `DEBUG` | `True` for local development, `False` in production | `True` |
   | `ALLOWED_HOSTS` | Comma-separated host names | `localhost,127.0.0.1` |

5. **Create the database**

   ```bash
   python manage.py migrate
   ```

6. **Create the guest accounts** (see below)

   ```bash
   python manage.py create_guest_users
   ```

7. **Optional: create an admin user** for the Django admin at `/admin/`.
   Only staff users may delete orders.

   ```bash
   python manage.py createsuperuser
   ```

8. **Start the server**

   ```bash
   python manage.py runserver
   ```

   The API is now available at `http://127.0.0.1:8000/api/`.

## Connecting the frontend

CORS is allowed for `http://127.0.0.1:5500` and `http://localhost:5500`, the
default address of the VS Code extension *Live Server*. Open the frontend
with Live Server and make sure its `shared/scripts/config.js` points to
`http://127.0.0.1:8000/api/`. For another frontend address, add it to
`CORS_ALLOWED_ORIGINS` in `core/settings.py`.

## Guest accounts

The frontend offers a guest login for both user types. Create (or reset) these
accounts after running the migrations:

```bash
python manage.py create_guest_users
```

| Type     | Username | Password   |
| -------- | -------- | ---------- |
| customer | `andrey` | `asdasd`   |
| business | `kevin`  | `asdasd24` |

The command is idempotent: running it again restores the passwords, profile
types and tokens of both guests.

## Authentication

Registration and login return a token. Send it with every request that needs
authentication:

```
Authorization: Token <your-token>
```

Unless an endpoint is marked as public below, a valid token is required.

## API endpoints

All endpoints start with `/api/`.

### Authentication

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| POST | `/api/registration/` | Register a customer or business user, returns a token | Public |
| POST | `/api/login/` | Log in with username and password, returns a token | Public |

### Profiles

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| GET | `/api/profile/{user_id}/` | Profile of a user | Authenticated |
| PATCH | `/api/profile/{user_id}/` | Update the profile (incl. picture upload) | Profile owner |
| GET | `/api/profiles/business/` | All business profiles | Authenticated |
| GET | `/api/profiles/customer/` | All customer profiles | Authenticated |

### Offers

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| GET | `/api/offers/` | Paginated list of offers | Public |
| POST | `/api/offers/` | Create an offer with exactly three details (basic, standard, premium) | Business users |
| GET | `/api/offers/{id}/` | Single offer | Authenticated |
| PATCH | `/api/offers/{id}/` | Update an offer and its details | Offer creator |
| DELETE | `/api/offers/{id}/` | Delete an offer | Offer creator |
| GET | `/api/offerdetails/{id}/` | Single offer package | Authenticated |

Query parameters for `GET /api/offers/`:

| Parameter | Description |
| --------- | ----------- |
| `creator_id` | Only offers of this user |
| `min_price` | Offers whose cheapest package costs at least this amount |
| `max_delivery_time` | Offers deliverable within this number of days |
| `search` | Search in title and description |
| `ordering` | `updated_at`, `min_price` (prefix `-` for descending), default `-updated_at` |
| `page`, `page_size` | Pagination, 6 offers per page by default, at most 100 |

### Orders

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| GET | `/api/orders/` | Orders where the user is customer or business user | Authenticated |
| POST | `/api/orders/` | Order an offer package (`offer_detail_id`) | Customers |
| PATCH | `/api/orders/{id}/` | Change the status (`in_progress`, `completed`, `cancelled`) | Business user of the order |
| DELETE | `/api/orders/{id}/` | Delete an order | Staff users |
| GET | `/api/order-count/{business_user_id}/` | Number of orders in progress | Authenticated |
| GET | `/api/completed-order-count/{business_user_id}/` | Number of completed orders | Authenticated |

### Reviews

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| GET | `/api/reviews/` | List of reviews | Authenticated |
| POST | `/api/reviews/` | Review a business user (one review per business user) | Customers |
| PATCH | `/api/reviews/{id}/` | Update `rating` and `description` | Review author |
| DELETE | `/api/reviews/{id}/` | Delete a review | Review author |

Query parameters for `GET /api/reviews/`: `business_user_id`, `reviewer_id`
and `ordering` (`updated_at` or `rating`, prefix `-` for descending).

### Base info

| Method | Endpoint | Description | Access |
| ------ | -------- | ----------- | ------ |
| GET | `/api/base-info/` | Number of reviews, average rating, number of business profiles and offers | Public |

### Status codes

| Code | Meaning |
| ---- | ------- |
| 200 / 201 / 204 | Success |
| 400 | Invalid data (also unknown fields in the request body) |
| 401 | Not authenticated |
| 403 | Authenticated, but not allowed (wrong user type or not the owner) |
| 404 | Object not found |

## Running the tests

The project was developed test-driven. Each app has its tests in `tests.py`.

```bash
python manage.py test --settings=core.test_settings
```

`core/test_settings.py` uses the fast MD5 password hasher, which makes the
test run much quicker. `python manage.py test` with the normal settings works
as well.

## Project structure

```
coderr_backend/
├── core/               # Settings, root URLs, test settings and test helpers
├── auth_app/           # Registration, login, create_guest_users command
├── profile_app/        # User profiles (customer / business)
├── offers_app/         # Offers and offer details, filters, pagination
├── orders_app/         # Orders and order counts
├── reviews_app/        # Reviews
├── base_info_app/      # Platform statistics
├── .env.template       # Template for the .env file
├── manage.py
└── requirements.txt
```

Every app keeps its API code in an `api/` package (`serializers.py`,
`views.py`, `urls.py`, `permissions.py`).

## Notes

- `db.sqlite3`, `media/` and `.env` are excluded from Git.
- Uploaded files are stored in `media/` and served by `runserver` while
  `DEBUG=True`.
- Prices are returned as numbers, not strings (`COERCE_DECIMAL_TO_STRING = False`).
