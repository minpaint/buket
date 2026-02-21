# Buket.by Implementation Plan (v1)

## 1. Scope and sequencing

### Goal of this plan
Build the project in two major stages:
1. Launch the main domain `buket.by` with a full catalog and stable data model.
2. Scale the same logic to 3 branch subdomains with isolated branch administration and storefront aggregation.

### Approved domains
- Main domain: `buket.by` (main office: Komsomolskaya street)
- Subdomains:
  - `dana-mall.buket.by`
  - `gallery-minsk.buket.by`
  - `minsk-city-mall.buket.by`

### Fixed product decisions
- Stack: one Django/DRF backend + one DB + one Next.js frontend.
- Roles at launch: `SuperAdmin`, `BranchAdmin`, `ContentManager`.
- BranchAdmin relation: strict 1:1 (one admin -> one branch).
- Availability model: `available_now + qty`.
- Special rule: if `available_now=true` and `qty=0` -> show badge `Predzakaz`.
- Product card actions: show both buttons (`Order` and `Contact`).
- Migration: copy products to all branches including images (initial seed).
- Media upload for branches: via frontend cabinet.
- Super admin panel: keep Django Admin.
- Branch cabinet route: use `/cabinet` (not `/admin`).
- Popular sorting: by views.
- SEO: do not duplicate product detail pages on main domain.
- Sitemap: one host-aware generator.
- Cache backend: Redis, TTL = 120 seconds.

## 2. High-level architecture

### Runtime topology (production)
- Public entrypoint: `Nginx` on `443`.
- Internal services:
  - Next.js app on internal port (example `3000`).
  - Django app on internal port (example `8000`).
  - Redis cache.
- Nginx routing:
  - `/` -> Next.js
  - `/api` -> Django
  - `/admin` -> Django Admin
  - `/media` -> media storage (nginx or Django depending deployment)

### Host-based behavior
- Frontend detects host (`buket.by` or subdomain) and resolves active branch context.
- Backend validates branch isolation on every branch-scoped endpoint.

## 3. Delivery phases

## Phase A: Main domain foundation (first priority)

### A1. Backend data model hardening
- Add/confirm models and fields:
  - `Branch`: name, subdomain, address, phone, work_time, geo, is_active.
  - Custom `User` role + optional `branch` FK.
  - `Category` (shared).
  - `Product`: branch FK, slug, availability fields, priority, lead_time_min, soft delete fields.
  - `ProductImage`: cover flag, order.
  - `Tag/Occasion`.
  - `AuditLog` minimal schema.
- Constraints/indexes:
  - unique `(branch, slug)`.
  - indexes for `branch`, `available_now`, `qty`, `priority`, `updated_at`.

### A2. Main domain API set
- Implement/align endpoints for catalog usage:
  - `GET /api/branches`
  - `GET /api/branches/{id}/available?limit=12`
  - `GET /api/branches/{id}/catalog?...`
  - `GET /api/products/{slug}` (branch-aware)
- Add filters:
  - price range, size, color, tags, lead_time bucket.
- Add sorting:
  - priority, views, price.
- Product details payload should include:
  - images, price/old_price, availability status, qty, lead_time, badges.

### A3. Main domain frontend catalog
- Build/verify pages for main domain first:
  - `/` (hero + category highlights + selected offers)
  - `/catalog`
  - `/product/[slug]`
  - `/contacts`
- Product card UX:
  - show `Predzakaz` when `available_now=true && qty=0`.
  - show both actions: `Order` + `Contact`.
- Messengers:
  - render standard Telegram/WhatsApp/Viber icons in contact block and card CTA area.
  - links come from branch/global contact settings in backend.

### A4. Admin minimum for content operations
- Django Admin for SuperAdmin:
  - branches, users, categories, products, images, tags.
- ContentManager permissions:
  - edit content pages/blocks for main domain without product pricing control.

### A5. Data migration normalization
- Parse branch contacts from `https://buket.by/kontakty.html` and save as source-of-truth.
- Ensure all migrated products have:
  - category, price, slug, at least one image.
- Seed products into all 3 branches with media copy.

### A6. Main domain acceptance gate
- Done criteria:
  - Main catalog works end-to-end on `buket.by`.
  - Product pages open with correct images.
  - Availability badges and filters work.
  - Contact page shows real branch contacts.

## Phase B: Branch cabinet and branch storefronts

### B1. RBAC enforcement
- Implement strict role checks in DRF permissions.
- BranchAdmin is limited to its own branch objects (403/404 on cross-branch access).
- Add audit entries on product/price/availability/image updates.

### B2. Branch cabinet (`/cabinet`)
- Auth for branch users.
- Product CRUD UI for branch:
  - create/edit/archive product
  - manage `available_now`, `qty`, `price`, `old_price`, `priority`, `lead_time_min`
  - image upload, cover selection, ordering
- Quick availability screen:
  - toggle in-stock in grid
  - bulk update availability
  - bulk update prices

### B3. Branch storefront routes
- On each subdomain implement:
  - `/`
  - `/available`
  - `/catalog`
  - `/product/[slug]`
  - `/contacts`
- Branch data strictly host-scoped.

### B4. Branch acceptance gate
- BranchAdmin can manage only own inventory.
- Storefront on each subdomain shows only own products.

## Phase C: Aggregator on main domain

### C1. Aggregator blocks on homepage
- Show 3 `Where to buy` blocks (one per branch):
  - branch name/address/phone/work time
  - route/map link
  - 6-12 available items
  - button to subdomain storefront
- Empty state:
  - `Storefront is updating` + branch link.

### C2. Cache strategy
- Store branch available snapshots in Redis.
- Invalidate/update on product availability changes (debounced).
- Scheduled refresh every 1-3 minutes.
- On update failure:
  - serve last valid cache
  - log error.

### C3. Aggregator acceptance gate
- Main homepage remains stable if one branch fails refresh.
- Cached branch data is still rendered with last successful timestamp.

## Phase D: SEO, performance, production hardening

### D1. SEO
- Host-aware metadata/canonical.
- Main domain indexes home and contacts.
- No full product duplicates on main domain.
- Unified sitemap generator supporting host context.

### D2. Media and optimization
- Auto image compression on upload.
- Generate optimized derivatives (JPG/WebP, and AVIF if supported in pipeline).
- Lazy loading on frontend.

### D3. Security and transport
- HTTPS only.
- Login rate limit.
- Strong password policy for admins.
- Correct CORS/CSRF for Next.js <-> DRF.

### D4. Deployment baseline
- Docker or systemd units (choose one implementation path).
- Nginx vhost config for main + 3 subdomains.
- Backups for DB + media.

## 4. API backlog (implementation checklist)

### Public
- `GET /api/branches`
- `GET /api/branches/{id}/available`
- `GET /api/branches/{id}/catalog`
- `GET /api/products/{slug}` (branch-aware)

### Auth
- `POST /api/auth/login`
- `POST /api/auth/refresh` (if JWT refresh)

### Branch cabinet
- `GET /api/admin/products`
- `POST /api/admin/products`
- `PATCH /api/admin/products/{id}`
- `POST /api/admin/products/bulk-availability`
- `POST /api/admin/products/bulk-price`
- `POST /api/admin/images/upload`

### Observability/internal
- `GET /api/internal/health`
- `GET /api/internal/cache-status` (superadmin only)

## 5. Testing and acceptance plan

### Automated tests
- Unit:
  - availability predicate (`available_now + qty` + preorder badge condition)
  - role permissions
- API:
  - branch isolation tests (read/write forbidden across branches)
  - catalog filters/sort tests
- Integration:
  - cache fallback behavior when branch update fails

### Manual QA scenarios
- Main domain:
  - catalog filters, product page, messenger icons, contacts.
- Branch cabinet:
  - bulk availability/price update, image upload, archive flow.
- Subdomains:
  - host-based branch rendering.
- SEO:
  - canonical and sitemap output per host.

## 6. Suggested implementation order (execution)

1. Data model + migrations + indexes.
2. Public catalog APIs for main domain.
3. Main domain frontend pages and product cards.
4. Data validation + branch contacts import.
5. RBAC + branch cabinet backend APIs.
6. Branch cabinet frontend (`/cabinet`).
7. Subdomain storefront host mapping.
8. Aggregator blocks + Redis cache/fallback.
9. SEO/performance/security hardening.
10. Production deployment with Nginx on 443.

## 7. Non-goals for v1

- 2FA.
- Complex order management workflows/CRM integrations.
- Fine-grained audit retention/rotation policies.

## 8. First actionable sprint (next step)

### Sprint-1 target (main domain catalog live)
- Finalize models and migrations for branch-scoped products.
- Expose catalog APIs for one active branch context on main domain.
- Build `/catalog`, `/product/[slug]`, `/contacts` on frontend.
- Connect real contact data and messenger icon links.
- Verify end-to-end via local run (`frontend:3001`, `backend:3002`).
