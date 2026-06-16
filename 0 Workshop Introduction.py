# Databricks notebook source
# MAGIC %md
# MAGIC ![DB Academy](./Includes/images/db-academy.png)

# COMMAND ----------

# MAGIC %md
# MAGIC # Lakebase Workshop
# MAGIC
# MAGIC For decades, **databases** have been the backbone of software, yet while we've completely reinvented how applications are built, the underlying databases have changed very little since the 1980s — suffering from fragile and costly operations, clunky development experiences, and extreme vendor lock-in.
# MAGIC
# MAGIC **Lakebase** represents a new approach: an open database architecture that brings together the reliability of transactional systems with the scalability and cost efficiency of the data lake. At its core is a rethinking of how databases are built — decoupling compute from storage so that data lives in affordable cloud object storage using open formats, while the database engine operates independently on top. This design removes much of the overhead, rigidity, and lock-in that traditional databases have carried for decades.
# MAGIC
# MAGIC **Databricks Lakebase** delivers this architecture as a fully managed, serverless Postgres database. Compute resources scale up automatically to meet demand and scale back to zero when not in use, so you only pay for what you consume. This makes it well suited for variable workloads, developer sandboxes, and AI agents that need to spin up isolated environments on the fly.
# MAGIC
# MAGIC <br>
# MAGIC
# MAGIC ```
# MAGIC                         ┌─────────────────────────────────────────────────────────────┐
# MAGIC                         │                        COMPUTE LAYER                        │
# MAGIC                         │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐    │
# MAGIC                         │  │ Endpoint A  │   │ Endpoint B  │   │   Endpoint C    │    │
# MAGIC                         │  │ (read-write)│   │ (read-only) │   │   (read-only)   │    │
# MAGIC                         │  └──────┬──────┘   └──────┬──────┘   └────────┬────────┘    │
# MAGIC                         │         │                 │                   │             │
# MAGIC                         ├─────────┼─────────────────┼───────────────────┼─────────────┤
# MAGIC                         │         │         STORAGE LAYER               │             │
# MAGIC                         │  ┌──────▼─────────────────▼───────────────────▼────────┐    │
# MAGIC                         │  │            Shared Object Storage (S3 / ADLS)        │    │
# MAGIC                         │  │   Branch: production  │  Branch: dev-feature  │ ... │    │
# MAGIC                         │  └─────────────────────────────────────────────────────┘    │
# MAGIC                         └─────────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC ### What this means in practice
# MAGIC
# MAGIC | Concept | Explanation |
# MAGIC |---------|-------------|
# MAGIC | **Compute (Endpoints)** | Each branch has one or more *endpoints* — PostgreSQL-compatible connection targets that process queries. Endpoints can scale up, scale down, or reach zero when idle, without touching your data. |
# MAGIC | **Storage (Branches)** | All branch data lives in object storage. Because storage is separate from compute and Lakebase uses copy-on-write technology, creating a branch is **zero-copy** — no data is physically duplicated. A branch only consumes extra storage as changes diverge from its source. |
# MAGIC | **Scale-to-Zero** | When there is no traffic or activity, the compute layer scales to zero, eliminating cost. The data remains safely in storage and the endpoint resumes instantly on the next connection. |
# MAGIC | **Independent Scaling** | You can attach multiple endpoints to a single branch (e.g. one read-write, plus read-only endpoints for additional read operations). |

# COMMAND ----------

# MAGIC %md
# MAGIC # DataCart: Modernizing E-Commerce Database Operations
# MAGIC
# MAGIC ---
# MAGIC
# MAGIC ### Current State: Life on a Traditional Database
# MAGIC
# MAGIC DataCart is a fast-growing global e-commerce company gearing up for a major **Spring Sale** — but its traditional Postgres setup is straining as the business and the engineering team scale:
# MAGIC
# MAGIC - **Overprovisioned and expensive** — DataCart pays for a bigger compute instance than it needs most of the time, and with no scale-to-zero it keeps paying even when the database sits idle.
# MAGIC - **A single shared dev database** — developers work against one shared database, leading to schema conflicts during development. That shared database also drifts out of sync with production, forcing full refreshes every weekend.
# MAGIC - **Brittle, hand-built ETL in both directions** — custom pipelines push promotion data from Databricks into the app, and sync app data back to Databricks for analytics. They are costly to run and increasingly hard to maintain as data grows.
# MAGIC - **No quick incident recovery** — a DevOps engineer once dropped a production table by mistake, taking key storefront functionality down for hours and costing real revenue.
# MAGIC
# MAGIC ### What the Team Wants
# MAGIC
# MAGIC - Pay only for the capacity they actually use.
# MAGIC - Give every developer an isolated, production-like database — without weekend refreshes.
# MAGIC - Move data between the app and the lakehouse **without building and babysitting ETL**.
# MAGIC - Recover from a bad change in seconds, not hours.
# MAGIC
# MAGIC This is the journey you'll walk through in the labs — starting from a freshly provisioned Lakebase project and ending with a fully modernized, governed, bidirectionally-synced operational database powering the Spring Sale.
# MAGIC
# MAGIC ### The DataCart Storefront
# MAGIC
# MAGIC Throughout this workshop, you'll interact with the **DataCart Storefront** — a live customer-facing e-commerce web application connected to your Lakebase project. As you run each lab, the storefront **evolves in real time**:
# MAGIC
# MAGIC | Lab | What Happens |
# MAGIC |-----|-------------|
# MAGIC | **1 Setup** | Basic storefront — products, stock, cart, orders (no ratings yet) |
# MAGIC | **2 Permissions** | Storefront comes online once the service principal has database access |
# MAGIC | **3 Parallel Dev** | No storefront change — branches are isolated from production |
# MAGIC | **4 Schema to Prod** | Star ratings, loyalty badges, "Earn pts" labels appear |
# MAGIC | **5 PITR Disaster** | Orders page breaks → gracefully degrades → recovers after PITR |
# MAGIC | **6 Reverse ETL** | Sale badges, discount prices, "Spring Sale Deals" section appear |
# MAGIC | **7 Lakehouse Sync** | Lakebase tables continuously mirror to Delta in Unity Catalog |
# MAGIC
# MAGIC > The storefront auto-detects schema changes every 30 seconds. No redeployment needed.
# MAGIC
# MAGIC ### This Workshop
# MAGIC
# MAGIC This workshop places you in the role of a database engineer at **DataCart**, a rapidly growing global e-commerce platform preparing for a major "Spring Sale" launch. You'll experience firsthand how Lakebase reverse ETL, Lakehouse Sync, branching, and PITR address real-world development and operational challenges.
# MAGIC
# MAGIC ### Key Learning Objectives
# MAGIC
# MAGIC | Topic | Description |
# MAGIC |---|---|
# MAGIC | **Serverless Autoscaling & Scale-to-Zero** | Paying only for the compute you use, with compute scaling to zero when idle |
# MAGIC | **Roles & Permissions** | Managing access control across branches to enforce governance |
# MAGIC | **Branching** | Creating isolated environments for parallel schema evolution across multiple developer teams |
# MAGIC | **Point-in-Time Recovery** | Recovering from catastrophic human error in seconds using PITR |
# MAGIC | **Reverse ETL (UC → Lakebase)** | Serving lakehouse analytics data to applications via synced tables — no ETL pipelines |
# MAGIC | **Lakehouse Sync (Lakebase → UC)** | Continuously mirroring OLTP tables to Delta for analytical workloads — no ETL pipelines |

