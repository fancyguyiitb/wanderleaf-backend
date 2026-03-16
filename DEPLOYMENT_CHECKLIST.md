# Wanderleaf Deployment Checklist

Use this as a practical launch checklist for the current stack:

- Frontend: Next.js on Vercel
- Backend: Django on Railway or Render
- Database: Neon or another managed Postgres
- Media: Cloudinary
- Realtime: Redis for Channels/chat in production

## 1. Accounts And Services

- [ ] Create or confirm accounts for Vercel, Railway or Render, Neon, Cloudinary, and Redis.
- [ ] Decide your production frontend domain and backend domain.
- [ ] Confirm which payment mode you want in production: test or live Razorpay keys.

## 2. Backend Environment Variables

- [ ] Set `DJANGO_SECRET_KEY` to a strong random production secret.
- [ ] Set `DJANGO_ALLOWED_HOSTS` to your live backend domain.
- [ ] Set `DATABASE_URL` to your production Postgres connection string.
- [ ] Set `CORS_ALLOW_ALL_ORIGINS=false` for production.
- [ ] Set Cloudinary values: `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`.
- [ ] Set Razorpay keys.
- [ ] Set email values if booking emails should be enabled.
- [ ] Set `CHANNELS_REDIS_URL` if chat / realtime features must work in production.

## 3. Frontend Environment Variables

- [ ] Set `NEXT_PUBLIC_API_BASE_URL_DEV` for local development.
- [ ] Set `NEXT_PUBLIC_API_BASE_URL_PROD` to the live backend URL.
- [ ] Add any other frontend public env vars required by your deployment platform.

## 4. Backend Production Setup

- [ ] Deploy the Django backend as an ASGI-capable service.
- [ ] Install dependencies successfully on the host.
- [ ] Run database migrations against production.
- [ ] Collect static files if your platform does not do it automatically.
- [ ] Verify the backend health endpoint or admin loads without server errors.
- [ ] Confirm media uploads reach Cloudinary successfully.

## 5. Database

- [ ] Create the production Postgres database.
- [ ] Verify SSL is enabled for the hosted database connection.
- [ ] Run migrations on the production database.
- [ ] Create a superuser if you need Django admin access.
- [ ] Back up the database connection details somewhere safe.

## 6. Realtime And Background Dependencies

- [ ] Provision Redis for Django Channels if messaging/chat is enabled.
- [ ] Confirm websocket connections work against the production backend.
- [ ] Verify notifications or live updates still function after deploy.

## 7. Security Hardening

- [ ] Rotate any secrets that were ever exposed in screenshots, chat, commits, or shared files.
- [ ] Make sure `.env` is ignored by git and not committed.
- [ ] Keep `DEBUG=False` in production.
- [ ] Restrict allowed origins and hosts to real domains only.
- [ ] Use HTTPS for frontend and backend.

## 8. End-To-End Verification

- [ ] Open the frontend and verify it can reach the backend.
- [ ] Test signup and login.
- [ ] Test creating a listing.
- [ ] Test image upload.
- [ ] Test booking creation.
- [ ] Test payment flow.
- [ ] Test host dashboard earnings and bookings.
- [ ] Test chat or messaging if enabled.
- [ ] Test logout and token expiry behavior.

## 9. Post-Launch

- [ ] Add a custom domain.
- [ ] Turn on uptime monitoring and error logging.
- [ ] Set up automated backups where available.
- [ ] Add a staging environment if you plan to keep iterating quickly.
- [ ] Document your production env vars in a safe internal place.

## Suggested First Deployment Order

1. Deploy the backend.
2. Configure the production database and run migrations.
3. Deploy Redis if you need realtime chat.
4. Test backend endpoints directly.
5. Deploy the frontend and point it at the live backend.
6. Run a full booking flow test.
