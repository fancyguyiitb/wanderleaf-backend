## Wanderleaf Backend (Django)

This is the backend for the **Wanderleaf** Airbnb-style application.
It is a modular Django REST API designed as a modern monolith and intended
to run against a managed Postgres database (e.g. Neon or any other
cloud PostgreSQL provider).

### Tech stack

- **Django 5**
- **Django REST Framework**
- **PostgreSQL** (Supabase in production)
- **JWT auth** (djangorestframework-simplejwt + dj-rest-auth + django-allauth)
- **Django Channels + Redis** for real-time features (chat, live updates)

### High-level structure

- `config/` – Django project configuration (settings, ASGI/WSGI, URLs)
- `apps/` – Domain apps:
  - `users/` – authentication, profiles, roles (hosts / guests)
  - `listings/` – properties, amenities, images
  - `bookings/` – reservations, availability, cancellation rules
  - `payments/` – payment intents, webhooks (Stripe or similar)
  - `reviews/` – property and host reviews and ratings
  - `messaging/` – conversations, chat, notifications
  - `common/` – shared utilities, base models, enums

This repository currently contains only the **skeleton**; the domain models,
serializers, views, and business logic will be implemented iteratively.

