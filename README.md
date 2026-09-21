# Lakebase-in-a-Box Workshop — App-Centric

This hands-on workshop introduces Databricks Lakebase — a fully managed, serverless PostgreSQL
database built on an open architecture that decouples compute from storage — and shows how to
leverage its capabilities to build and operate production-grade applications with unusual agility.

You step into the role of a developer at **DataCart**, a rapidly growing e-commerce platform. The
stakes are high: the "Spring Sale" launch is weeks away, and your team needs to roll out a loyalty
program, a product-reviews feature, and performance optimizations — all while keeping the production
storefront bulletproof.

This is the **app-centric** edition: it centers on the live DataCart Storefront app, which evolves in
real time as each lab changes the database. You watch features appear, break, and recover in the
browser as you run each notebook.

---

## Notebooks at a glance

Run the notebooks in order. `0.1` provisions everything; the labs build on each other.

| # | Notebook | What it does |
|---|----------|--------------|
| 0 | `0 Workshop Introduction` | Workshop overview, Lakebase architecture, and the DataCart scenario |
| 0.1 | `0.1 Lab - Create Lakebase Project & App (using SDK)` | Provision the Lakebase project **and** the storefront app (and their binding) via the Databricks SDK |
| 1 | `1 Lab - Discover and Seed the Lakebase Project` | Discover the project, connect over OAuth, seed the `ecommerce` schema |
| 2 | `2 Lab - Roles Permissions and Connect Storefront` | Grant the app's service principal Postgres access and bring the storefront online |
| 3 | `3 Lab - Parallel Development with Branching` | Three developers evolve the schema in parallel on isolated, zero-copy branches |
| 4 | `4 Lab - Schema Migration to Production` | Promote validated changes from a feature branch to production (Migration Replay) |
| 5 | `5 Lab - Point in Time Recovery and Snapshots` | Simulate an accidental `DROP TABLE` and recover production with PITR |
| 6 | `6 Lab - Reverse ETL with Synced Tables (UC to Lakebase)` | Push Spring Sale promotions from a UC Delta table into Lakebase |
| 7 | `7 Lab - Lakebase CDF (Lakebase to UC)` | Continuously mirror live Lakebase tables into Delta in Unity Catalog |
| 8 | `8 Lecture - Read Replicas & Connection Pooling` | Scale reads with read-only replica endpoints and scale connections with the built-in PgBouncer pooler |
| 9 | `9 Workshop Summary` | End-to-end recap of everything you built |
| — | `CLEAN_UP - PLEASE RUN AT THE END!` | **Run last.** Deletes the Lakebase project and the storefront app to tear down all workshop resources |

> **⚠️ Unity Catalog target (Labs 6 & 7).** These labs write to a Unity Catalog catalog you
> control. Near the top of each, set:
> ```python
> UC_CATALOG = "<your-catalog-here>"
> ```
> to a catalog you can create schemas in (you need `CREATE SCHEMA` on it). The lab creates the
> `ecommerce` / `lakebase_to_lakehouse` schemas inside it.

---

## Lab-by-lab walkthrough — what happens after each

The storefront **auto-detects schema changes every ~30 seconds**. After running a lab, just refresh
the browser — no redeployment needed.

### Lab 0.1 — Create the Project & App (SDK)
**What you do:** Run one notebook that uses the Databricks SDK to create the Lakebase Autoscaling
project (`lakebase-workshop-<your-user-id>`), create the DataCart Storefront app
(`storefront-<your-user-id>`), and bind the project to the app as a database resource. The final step
is a manual one: point the app at its source code and click **Deploy**.

**After this lab:** The project and app exist. **When you deploy the app it will NOT show the
storefront yet — it displays a "Loading…" / connection error, and this is expected.** The app's
service principal has no Postgres access until Lab 2, so it cannot read the database. Don't try to
"fix" this now — it comes online in Lab 2.

### Lab 1 — Discover and Seed the Lakebase Project
**What you do:** Discover the project via the SDK, connect to Postgres using short-lived OAuth tokens
(no passwords), and seed the `ecommerce` schema with 5 tables — `customers`, `products`, `inventory`,
`orders`, `order_items` — using native PL/pgSQL (SERIAL keys, foreign keys, CHECK/UNIQUE constraints).

**After this lab:** The database has data, but the storefront **still shows "Loading…"** — the app's
service principal still hasn't been granted access. That's Lab 2.

### Lab 2 — Roles, Permissions, and Connecting the Storefront
**What you do:** Learn Lakebase's two permission layers (workspace project ACLs vs. database Postgres
roles). Grant the storefront's service principal `CAN USE` on the project, create its OAuth Postgres
role, and grant schema/table/sequence privileges (plus `ALTER DEFAULT PRIVILEGES` for future tables).

**After this lab — the storefront comes online! 🎉** Refresh the app and you'll see:
- Products with prices and stock badges (In Stock / Low Stock / Out of Stock)
- A working shopping cart and checkout
- Order history with status badges
- **No** star ratings, reviews, or loyalty features yet — those tables don't exist on production yet.

### Lab 3 — Parallel Development with Branching
**What you do:** Create isolated, zero-copy, TTL-expiring branches from production and simulate three
developers working simultaneously:
- `dev-loyalty-reviews` — adds `loyalty_points` column, `loyalty_members` table, and a `reviews` table
- `modify-orders` — adds `exchange_rates` table and migrates `currency` to a foreign key
- `add-index` — adds a price index on `products`

**After this lab:** **No change to the storefront** — all work lives on isolated branches, and
production is untouched. This is the whole point of branching: parallel work with zero impact on prod.

### Lab 4 — Schema Migration to Production
**What you do:** Use **Schema Diff** to compare the feature branch against production, confirm prod is
untouched, then replay the same idempotent DDL on production (Migration Replay). Also covers the
**Branch Reset** concept for refreshing branches from their parent.

**After this lab — loyalty & reviews go live! 🎉** Refresh the app:
- **Navbar** — a loyalty tier badge (Bronze/Silver/Gold/Platinum) with points count
- **Homepage** — a "Loyalty Program Active!" banner and a "Top Rated" section
- **Product cards** — star ratings, review counts, and "Earn X pts" labels
- **Product detail** — a full customer reviews section
- **Cart / checkout** — shows loyalty points you'll earn

### Lab 5 — Point-in-Time Recovery (PITR) & Snapshots
**What you do:** Record a pre-disaster timestamp, then simulate a "Code Red" incident —
`DROP TABLE orders CASCADE` on production. Create a PITR recovery branch from just before the drop,
verify the data is intact, and restore production by copying the recovered data back.

**During the disaster (graceful degradation):**
| Page | What you see |
|------|--------------|
| Home | Top Rated works; Best Sellers shows "temporarily unavailable" |
| Shop | Products still browsable with ratings and "Earn X pts" |
| Cart | Items remain, but checkout errors |
| Orders | "Orders Service Unavailable" with a "Continue Shopping" button |

**After recovery:** The Orders page returns with full history, Best Sellers works again, and checkout
is functional — production is fully restored, no redeployment needed.

### Lab 6 — Reverse ETL with Synced Tables (UC → Lakebase)
**What you do:** Create a Change-Data-Feed–enabled `promotions` Delta table in Unity Catalog (in your
`UC_CATALOG`), seed Spring Sale data, and create a managed **synced table** into the production
Lakebase branch. Re-grant the SP access to the new synced table.

**After this lab — promotions go live! 🎉**
- **Homepage** — a "Spring Sale Deals" section
- **Product cards** — red sale badges (e.g., "SPRING SALE -20%") with original prices struck through
- **Cart** — promoted items show the discounted price

All of this appears with **zero application code changes** — the marketing team just updated a Delta
table and the sync pipeline pushed it to Lakebase.

### Lab 7 — Lakebase CDF (Lakebase → UC)
**What you do:** Set `REPLICA IDENTITY FULL` on source tables, create a Lakebase CDF configuration that
continuously mirrors live `orders`, `customers`, and `order_items` into Delta in Unity Catalog, trigger
the initial snapshot, and run an analytics query against the Delta replica.

**After this lab:** **No storefront change** — this is the outbound analytics flow. You now have
"OLTP analytics without OLTP load": BI/ML queries hit Delta while the storefront keeps serving from
Lakebase.

### Lab 8 — Read Replicas & Connection Pooling (lecture)
**What you do:** A concept-focused lecture on scaling under Spring Sale load. Part 1 covers **read
replicas** — read-only compute endpoints (up to 6 per branch) that serve reads from the *same* shared
storage with no data copy — including an SDK snippet that adds a `read-replica-1` endpoint to the
production branch and reads from it. Part 2 covers **connection pooling** — the built-in PgBouncer
pooler (transaction mode, up to 10,000 client connections) exposed on the `-pooler` / `-ro-pooler`
hosts, and when to use a direct connection instead.

**After this lab:** **No storefront change** — this is a scaling/architecture lecture. There is **no
automatic read/write split**, so routing reads to a replica is a deliberate connection-config choice.
The one executable cell provisions a real read-only endpoint on your workshop project; the `CLEAN_UP`
notebook removes it along with the project.

### Lab 9 — Workshop Summary
A full recap of the DataCart story, the labs in order, and the Lakebase concepts behind each.

### CLEAN_UP — Please Run at the End!
Deletes the storefront app and the Lakebase project (all branches, compute, databases, and data).
**Run this once you're done** so nothing is left running.

---

## DataCart Storefront App

A customer-facing e-commerce web application (React + FastAPI) in `datacart-storefront/` that evolves
in real time as each lab modifies the database.

### Architecture

```
┌─────────────────────────────────────────────────────┐
│              DataCart Storefront App                  │
│  ┌─────────────┐        ┌────────────────────────┐  │
│  │ React UI    │  HTTP  │  FastAPI Backend        │  │
│  │ (Vite SPA)  │───────▶│  /api/shop/*            │  │
│  │             │        │  /api/cart/*            │  │
│  │ - Home      │        │  /api/orders/*          │  │
│  │ - Shop      │        └───────────┬────────────┘  │
│  │ - Product   │                    │ psycopg        │
│  │ - Cart      │                    │ OAuth tokens   │
│  │ - Orders    │                    ▼                │
│  └─────────────┘        ┌────────────────────────┐  │
│                         │  Lakebase (PostgreSQL)  │  │
│                         │  ecommerce schema       │  │
│                         │  production branch      │  │
│                         └────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

> **📍 Expect a blank / "Loading…" storefront right after you deploy the app (Lab 0.1).** The app
> runs as a **service principal** that has no database access until **Lab 2** grants it. This is
> normal — the store populates only after you complete Lab 2. If it's still not loading after Lab 2,
> see Troubleshooting.

### Feature timeline

| Feature appears | After |
|-----------------|-------|
| Storefront comes online (products, stock badges, cart, orders) | **Lab 2** (SP granted access) |
| Loyalty tier badge, points, "Earn X pts", star ratings, reviews | Lab 4 (schema promoted to production) |
| Graceful degradation, then recovery | Lab 5 (PITR disaster → restore) |
| Sale badges, discount prices, "Spring Sale Deals" | Lab 6 (Reverse ETL) |
| Analytics surface (no visible storefront change) | Lab 7 (Lakebase CDF) |
| Read/connection scaling (no visible storefront change) | Lab 8 (Read Replicas & Pooling — lecture) |

### Setup

The recommended path is the **`0.1` SDK notebook**, which creates the Lakebase project, the storefront
app, and the resource binding for you. After running it, the only manual step is pointing the app at
its source code and clicking **Deploy** (see the notebook's final section). Remember: the deployed app
will show "Loading…" until Lab 2.

<details>
<summary><strong>Alternative: manual / DABs app setup</strong></summary>

The `datacart-storefront/` folder includes an `app.yaml` and a `databricks.yml` bundle config.

**app.yaml** — set the project (do **not** hardcode `PGHOST`/`PGUSER`/`PGDATABASE`; those are injected
when you add the Lakebase database as an app resource):
```yaml
env:
  - name: LAKEBASE_PROJECT
    value: "<project-name>"      # lakebase-workshop-<your-user-id>
  - name: DB_SCHEMA
    value: "ecommerce"
resources:
  - name: postgres
    type: postgres
```

**Add the Lakebase resource before the first deploy** (Compute → Apps → Create App → Add Resource →
Database → your Lakebase project → *Can connect*). This injects the connection env vars on deploy.

**Deploy via DABs:**
```bash
cd datacart-storefront
# set your CLI profile in databricks.yml targets first
databricks bundle validate
databricks bundle deploy --target dev
```
</details>

---

## Troubleshooting

- **Storefront shows "Loading…" / "Store Unavailable" before Lab 2** — Expected. The service principal
  has no database access until Lab 2. Complete Lab 2 and refresh.
- **Still "Loading…" after Lab 2** — Hit `<app-url>/api/dbtest`. If `PGHOST` is `NOT SET`, the app was
  not redeployed after the Lakebase resource was added — redeploy. If `db_connected: false` with a
  password error, the SP role wasn't created; ensure the resource is added, then redeploy.
- **Endpoint scaled to zero** — the first request after idle can take ~10–20s while compute wakes;
  wait and refresh.
- **500 errors / missing features after a lab** — the SP may need grants on newly created tables. Labs
  that add tables re-grant the SP; re-run that grant step as the project owner if needed.
- **Sale deals not appearing (after Lab 6)** — synced tables are created by the sync pipeline, so
  `ALTER DEFAULT PRIVILEGES` doesn't cover them; re-run `GRANT ALL ON ALL TABLES IN SCHEMA ecommerce
  TO "<SP_CLIENT_ID>";` from Lab 6.
- **Logs:** `<app-url>/logz`

## Documentation

- [Lakebase Overview](https://docs.databricks.com/aws/en/oltp/)
- [Manage Branches](https://docs.databricks.com/aws/en/oltp/projects/manage-branches)
- [Point-in-Time Recovery](https://docs.databricks.com/aws/en/oltp/projects/point-in-time-restore)
- [Connect to Your Database](https://docs.databricks.com/aws/en/oltp/projects/connect)
- [Postgres Roles](https://docs.databricks.com/aws/en/oltp/projects/postgres-roles)
- [API Reference](https://docs.databricks.com/api/workspace/postgres)
