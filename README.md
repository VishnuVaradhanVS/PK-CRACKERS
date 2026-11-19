# Crackers Commerce — Django + PostgreSQL

Two portals:
- Customer storefront: registration/login, catalogue, cart, checkout, order history and order details.
- Staff portal: inventory, product uploads, order management, and editable checkout payment instructions/QR; Django admin provides full CRUD and search/filter controls.

## Quick start (Docker — recommended)
1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Edit `.env`: set a unique `DJANGO_SECRET_KEY`, `DJANGO_SUPERUSER_PASSWORD`, and `POSTGRES_PASSWORD` (the latter can be added as a line in `.env`).
4. Start:
   ```bash
   docker compose up --build
   ```
5. Visit http://localhost:8000
6. Staff dashboard: log in with the bootstrap admin credentials from `.env`, then open `/staff/`. Full admin: `/django-admin/`.

Docker Compose starts PostgreSQL, applies migrations, collects static assets and creates the configured superuser if it does not already exist.

## Run locally without Docker (SQLite development mode)
Requires Python 3.11+.
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```
Copy `.env.example` to `.env`. For non-Docker local use, set `DATABASE_URL=sqlite:///db.sqlite3`, `DJANGO_DEBUG=True`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`. Load environment variables:
```powershell
# Windows PowerShell
Get-Content .env | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object { $name,$value=$_.Split('=',2); Set-Item -Path "Env:$name" -Value $value }
```
On macOS/Linux, load the `.env` file into your shell with `set -a; . ./.env; set +a` before running Django commands. On Windows PowerShell, use the environment-loading command above.

Then:
```bash
python manage.py migrate
python manage.py ensure_admin
python manage.py runserver
```
Open http://127.0.0.1:8000.

## Tests and checks
```bash
python manage.py test
python manage.py check --deploy
```

## Data model
Product: id, name, description, cost, image_url, video_file, stock, is_active. (The old external video URL field is retained internally for existing database compatibility but is no longer exposed or displayed.)
Order: UUID id, user, username, contact, address, total_amount, status, created_at.
OrderItem: product, product_name and unit_price snapshots, quantity, line_total.

Stock is reserved/decremented inside a database transaction with row locking during checkout. Cancelling an order restores stock. Customer order detail pages are restricted to the owner.

## Production deployment checklist
This is a production-oriented starter, not a guarantee of production readiness. Before going live:
- Use a managed PostgreSQL database, HTTPS reverse proxy, strong unique secrets, secure cookie settings and a restricted `ALLOWED_HOSTS`.
- Set `DJANGO_DEBUG=False`, `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, and correct `CSRF_TRUSTED_ORIGINS`.
- Configure backups, monitoring, log aggregation, email delivery, error reporting, dependency scanning and a static/media object store.
- Add rate limiting / bot protection, MFA for staff, staff role permissions and audit logs.
- Integrate a payment gateway only after selecting a provider; verify payment webhooks server-side and never trust client-side payment success.
- Add order cancellation/refund policies, shipping rules, tax/invoice requirements, privacy policy, terms, retention and consent controls.
- Validate local fireworks/crackers licensing, age restrictions, storage, transport, delivery and sale requirements. Ensure products sold are lawful and appropriately certified. This starter does not determine legal eligibility or compliance.
- Load test and have a qualified security review before accepting real customer data or payments.

Payments are intentionally not enabled. Checkout records an order request; it does not charge the customer.


## Render deployment
The repository includes `render.yaml` for a Render Blueprint.
1. Push the project to a GitHub repository.
2. In Render, choose **New → Blueprint** and connect the repository.
3. Review the blueprint. It provisions PostgreSQL, a Docker web service and a persistent disk for uploaded images.
4. Set `DJANGO_SUPERUSER_PASSWORD` when prompted. Use a strong unique password.
5. If Render assigns a different hostname, update `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to that hostname and HTTPS origin.
6. Deploy. Staff sign in at `/accounts/login/`, manage inventory/orders at `/staff/`, and use `/django-admin/` for the full admin.

The blueprint uses paid Render service/database and persistent-disk plans. A persistent disk is required for uploaded images to survive deploys/restarts. Confirm current Render pricing, region availability and backup options before deploying.

## Manual payment workflow
Customers place orders without paying online. Orders start with payment status **Payment pending**. The admin contacts the customer and arranges payment outside the application, then marks **Payment received** in the staff dashboard or Django admin. An internal note can be added. Staff must independently verify bank/UPI receipt; this application does not automatically verify transfers.

## Product image upload
Sign in as staff and open `/staff/`. Use the Add product form and choose an image file. The app stores it under `MEDIA_ROOT/products/`. On Render, the blueprint mounts a persistent disk at `/var/data` and sets `MEDIA_ROOT=/var/data/media`. A separate object-storage/CDN service can be added later for larger scale.


Render disk note: a service with an attached persistent disk runs as a single instance and cannot use Render autoscaling. This is a practical starting point for a small storefront. For multi-instance scaling and CDN delivery, move uploaded images to S3-compatible object storage (or a managed media platform) and serve them through a CDN.


## Product video uploads
Staff can upload product videos directly from `/staff/`. Supported formats are MP4, WebM and Ogg, with a 100 MB application-level limit. Customers can play videos inline on product cards using the browser's native video controls. Uploaded videos are stored under `MEDIA_ROOT/product_videos/`; the existing Docker `media_data` volume and Render persistent disk also retain these uploads. Run `python manage.py migrate` after updating to apply migration `0003_product_video_file`.


## Checkout payment instructions and QR code
Staff can open `/staff/` and use the Payment settings section to update the checkout instructions and upload/replace a payment QR image (PNG/JPG/WebP accepted by Django's image backend; maximum 5 MB in the staff form). The QR and instructions appear to customers on checkout. Payment remains manual: the app does not initiate or verify UPI/bank transfers. Staff must verify receipt independently. The QR image is stored in `MEDIA_ROOT/payment_qr/` and therefore persists on the configured Docker volume or Render persistent disk.

## Visual design and product media sizing
The storefront uses a dark navy glass-inspired interface with white text and green, orange and pink accents. Product cards use a fixed media frame and consistent card layout; uploaded portrait/landscape images are displayed in a fixed crop frame, and videos play in a fixed-size contained player.

## Updating an existing installation
Keep your existing `.env` and Docker volumes. Replace the project code with this release, then run `docker compose up --build -d`. The entrypoint runs migrations automatically, including `0004_storepaymentsettings`. Do not run `docker compose down -v` when you need to preserve customer orders and uploads.

## Staff dashboard and cart experience (latest UI update)
The staff portal now uses three top-level tabs: **Inventory**, **Orders**, and **Payment info**. Only the selected panel is shown, and its active state uses the matching green, orange or pink accent. Inventory rows include fixed-size image and video previews. The add-product form sits beside a live customer-card preview that updates as staff type product details or select image/video files. The customer cart uses individual product cards with image thumbnails, plus/minus quantity controls and a remove (×) action. Subtle entrance/hover animations respect the device's reduced-motion preference. No database migration is required for this UI update.


## Latest staff and catalogue updates

- Product records can be created and edited directly in the staff portal using the same add/edit form and live preview.
- Shop and staff inventory include product-name search.
- Staff orders can be filtered by order status.
- Order status and manual payment status are saved together with one form submission.
- Existing Django admin URLs remain available for advanced administration.


## Email notifications

Staff can configure one or more admin notification addresses in **Staff → Payments → Payment instructions & QR → Admin notification email addresses**. Separate addresses with commas, semicolons, or new lines. Each configured address receives an email when a new order is placed. The customer account email receives an email when staff changes the order status or payment status.

For Render Free, use the Resend HTTPS API rather than SMTP (Render Free blocks outbound SMTP ports 25, 465, and 587). This project includes `store.email_backends.ResendEmailBackend`, which keeps the existing Django `EmailMultiAlternatives` calls and HTML/plain-text templates intact.

Configure these environment variables in Render → your web service → Environment:

- `EMAIL_PROVIDER=resend`
- `RESEND_API_KEY=re_...` (create a sending API key in the Resend dashboard; never commit it)
- `DEFAULT_FROM_EMAIL=PK CRACKERS <onboarding@resend.dev>` for initial testing
- `EMAIL_TIMEOUT=10`

**Important testing limitation:** Resend's shared `onboarding@resend.dev` sender is for testing, not production delivery to arbitrary customers. Without owning a domain, use Resend's documented test flow and verify that the sender/recipient combination is allowed by your Resend account. To send OTPs and order notifications to all customers, you will need to register a domain you control in Resend, add its SPF/DKIM DNS records at the domain provider, wait for verification, then change `DEFAULT_FROM_EMAIL` to an address on that verified domain (for example, `PK CRACKERS <orders@yourdomain.com>`). The sender address must match a verified sending domain.

Leave `EMAIL_PROVIDER` blank for local console email output. To retain legacy SMTP on a local or paid host, set `EMAIL_PROVIDER=smtp` and configure `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `EMAIL_USE_SSL`. Do not commit API keys or SMTP passwords to source control.

## Email notifications and templates

Order emails use editable Django templates in `templates/emails/`:

- `customer_order_confirmation.html` / `.txt`: sent to the customer after checkout.
- `admin_new_order.html` / `.txt`: sent to the notification addresses configured in Staff → Payments.
- `customer_order_update.html` / `.txt`: sent when staff changes order status or payment status.
- `base.html`: shared branded email layout.

The HTML templates use inline styles for compatibility with common email clients and have matching plain-text alternatives. Edit the corresponding template files to change the wording or presentation; no database migration is required.


## Optional WhatsApp order notifications (Meta Cloud API)

The application can send transactional WhatsApp notifications using Meta's official WhatsApp Cloud API. Email remains independent; a WhatsApp API error is logged and does not cancel checkout or prevent email delivery.

### 1. Configure Meta

1. Create a Meta developer app and add the WhatsApp product: https://developers.facebook.com/
2. Connect a WhatsApp Business Account and register the business sender number.
3. Create and get approval for the following **Utility** message templates in WhatsApp Manager. The names, language and body-variable order must match the configuration below. Set the template language to `en` (or change `WHATSAPP_TEMPLATE_LANGUAGE` to the exact language code used by your approved templates).

**`kk_order_confirmation`** (4 body variables):

```text
Hello {{1}}, your PK Crackers order #{{2}} has been received. Items: {{3}}. Order total: {{4}}. We will send further updates when your order changes.
```

**`kk_order_update`** (5 body variables):

```text
Hello {{1}}, there is an update for your PK Crackers order #{{2}}: {{3}}. Current order status: {{4}}. Payment status: {{5}}.
```

**`kk_admin_new_order`** (8 body variables):

```text
New PK Crackers order #{{2}} from {{1}}. Customer contact: {{3}}. Delivery address: {{4}}. Items: {{5}}. Total: {{6}}. Order status: {{7}}. Payment status: {{8}}.
```

Submit each template for Meta review and wait until its status is **Approved** before enabling sends. Include representative sample values for every variable when submitting. The application sends template messages because an order notification is normally initiated by the business; ordinary free-form messages are not permitted outside the customer's 24-hour service window. Customers and admin recipients must have opted in to receive WhatsApp messages.

### 2. Configure environment variables

Copy the values from Meta for Developers / WhatsApp Manager into your local `.env` file and Render service Environment settings. Never commit a real access token.

```env
WHATSAPP_ENABLED=True
WHATSAPP_NOTIFY_CUSTOMERS=True
WHATSAPP_NOTIFY_ADMINS=True
WHATSAPP_ACCESS_TOKEN=your_permanent_or_system_user_access_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_whatsapp_business_account_id
WHATSAPP_API_VERSION=v26.0
WHATSAPP_TEMPLATE_LANGUAGE=en
WHATSAPP_DEFAULT_COUNTRY_CODE=91
WHATSAPP_TEMPLATE_ORDER_CONFIRMATION=kk_order_confirmation
WHATSAPP_TEMPLATE_ORDER_UPDATE=kk_order_update
WHATSAPP_TEMPLATE_ADMIN_NEW_ORDER=kk_admin_new_order
```

Use a supported Graph API version available to your Meta app; `v26.0` is the version configured in this project at the time this integration was prepared. The business account ID is retained for configuration/reference; sends use the Phone Number ID.

### 3. Configure admin recipients

Open **Staff portal → Payments** and enter admin WhatsApp numbers in international format (for example `+919876543210`). Separate multiple numbers with commas, semicolons, or new lines. Only add recipients who have agreed to receive business alerts. Save payment settings.

### 4. Customer opt-in

At checkout, customers can tick the WhatsApp consent checkbox. The order's contact number is used as the WhatsApp destination. Enter the full number with country code; 10-digit Indian mobile numbers are prefixed with `91` based on `WHATSAPP_DEFAULT_COUNTRY_CODE`. Customers who do not tick the box will continue to receive email notifications but will not receive WhatsApp messages.

### 5. What gets sent

- New order: customer confirmation (only with checkout opt-in) and admin alert(s).
- Order status change: customer update (only with checkout opt-in).
- Payment status change: customer update (only with checkout opt-in).

The app logs API rejections and network failures without exposing the access token. A successful API response means Meta accepted the message request; it does not by itself confirm delivery.


## PK Crackers brand assets and contact details
The storefront and branded email templates use the supplied PK Crackers seal and monogram from `store/static/store/images/`. The public contact links are WhatsApp **9499013251** and phone **6369655972**. The header includes the requested faith symbols.


## Password reset and account email uniqueness

Customers can use **Forgot your password?** on the login page to request a secure password-reset link by email. Django generates a one-time tokenized link; the reset pages and branded email use PK Crackers styling. Password reset email delivery uses the same configured Django email backend as signup OTPs and order emails. On Render Free, configure Resend as described in the Email notifications section above; local development can use the console backend.

Signup rejects an email address already used by another account, case-insensitively. Email addresses are stored in lowercase. A database-level case-insensitive unique constraint also protects against simultaneous signup requests. Migration `0008_unique_user_email` checks for existing duplicate non-empty email addresses before adding the constraint. If duplicates already exist, the migration stops with the duplicate addresses listed; resolve those accounts before deploying the migration. It does not delete or merge customer accounts automatically.


## Login, password reset, and email-verified signup

- Customers can log in using either their username or registered email address (email matching is case-insensitive).
- Password reset checks for an active account before sending. Unknown addresses receive a clear form error and no email is sent. Reset emails explicitly show the account username.
- New registrations require a six-digit email OTP before a user account is created. Codes expire after 10 minutes, are stored hashed, are single-use, and allow at most five attempts. Resending is limited to once per minute.
- OTP, password reset, and order notification emails all use the configured Django email backend (Resend HTTPS API on Render Free, or console/SMTP where configured).
- Migration `0009_emailverificationotp` creates the short-lived OTP table. Existing customer accounts are not changed.
