# Databricks notebook source
# MAGIC %md
# MAGIC # 📈 Lecture 8: Scaling Reads — Read Replicas & Connection Pooling
# MAGIC
# MAGIC The Spring Sale is live and traffic on the DataCart storefront has spiked. Two very
# MAGIC different pressures show up under load:
# MAGIC
# MAGIC 1. **Read volume** — thousands of shoppers browsing products, ratings, and promotions
# MAGIC    generate far more *reads* than writes.
# MAGIC 2. **Connection count** — a busy web/API tier opens many short-lived database
# MAGIC    connections, which can exhaust Postgres' connection budget.
# MAGIC
# MAGIC Lakebase addresses these with two independent features:
# MAGIC
# MAGIC | Pressure | Feature | What it does |
# MAGIC |----------|---------|--------------|
# MAGIC | Too many reads | **Read replicas** | Add read-only computes that serve reads from the *same* storage — no data copy |
# MAGIC | Too many connections | **Connection pooling** | A built-in **PgBouncer** pooler multiplexes many client connections onto few server connections |
# MAGIC
# MAGIC > 📖 **Docs**: [Read replicas](https://docs.databricks.com/aws/en/oltp/projects/read-replicas) · [Connection pooling](https://docs.databricks.com/aws/en/oltp/projects/connection-pooling)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 1 — Read Replicas
# MAGIC
# MAGIC A **read replica** is an independent, **read-only** compute endpoint attached to a branch.
# MAGIC Because Lakebase separates compute from storage, replicas do **not** copy your data —
# MAGIC every compute (the primary read-write endpoint and all replicas) reads from the **same
# MAGIC shared storage layer**, so they see a consistent view of the data.
# MAGIC
# MAGIC ```
# MAGIC                 Branch: production
# MAGIC   ┌────────────────────┬────────────────────┬────────────────────┐
# MAGIC   │  primary            │  read-replica-1     │  read-replica-2     │
# MAGIC   │  (read-write)       │  (read-only)        │  (read-only)        │
# MAGIC   └─────────┬───────────┴──────────┬─────────┴──────────┬─────────┘
# MAGIC             │                      │                    │
# MAGIC             ▼                      ▼                    ▼
# MAGIC   ┌───────────────────────────────────────────────────────────────┐
# MAGIC   │              Shared object storage (no duplication)           │
# MAGIC   └───────────────────────────────────────────────────────────────┘
# MAGIC ```
# MAGIC
# MAGIC **Key facts (from the docs):**
# MAGIC - You can add **up to 6 read replicas per branch**.
# MAGIC - Replicas involve **no data duplication or replication** — all computes read from the
# MAGIC   same storage, ensuring a consistent source.
# MAGIC - There is **no automatic read/write split**. Your application must connect to the
# MAGIC   **replica endpoint explicitly** to send read traffic to it; writes continue to go to
# MAGIC   the primary read-write endpoint.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Add a read replica — via the UI
# MAGIC
# MAGIC In the Lakebase app, open your project → **production** branch → the **Computes** tab →
# MAGIC click **Add Read Replica** to instantly provision a new read-only compute.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Add a read replica — via the SDK
# MAGIC
# MAGIC A read replica is simply an endpoint with `endpoint_type = ENDPOINT_TYPE_READ_ONLY`.
# MAGIC The snippet below adds one to the `production` branch of the workshop project.

# COMMAND ----------

# MAGIC %pip install "databricks-sdk>=0.89.0" -q
# MAGIC %pip install "psycopg[binary]" -q

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import Endpoint, EndpointSpec, EndpointType

w = WorkspaceClient()

# Derive the same project name used throughout the workshop (created in Lab 0.1)
db_user = w.current_user.me().user_name
project_name = f"lakebase-workshop-{w.current_user.me().id}"
branch_path = f"projects/{project_name}/branches/production"

# Create a read-only endpoint (a read replica) on the production branch
replica = w.postgres.create_endpoint(
    parent=branch_path,
    endpoint_id="read-replica-1",
    endpoint=Endpoint(spec=EndpointSpec(
        endpoint_type=EndpointType.ENDPOINT_TYPE_READ_ONLY,
        autoscaling_limit_min_cu=0.5,
        autoscaling_limit_max_cu=2.0,
    )),
).wait()

print(f"✅ Read replica created on {branch_path}")
print(f"   Endpoint: {replica.name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Connecting to the replica
# MAGIC
# MAGIC Point read-heavy queries at the **replica's** host (the primary keeps serving writes).
# MAGIC The connection pattern is identical to the primary — generate an OAuth token for the
# MAGIC replica endpoint and connect with `psycopg`.

# COMMAND ----------

import psycopg

replica_host = replica.status.hosts.host
cred = w.postgres.generate_database_credential(endpoint=replica.name)

read_conn = psycopg.connect(
    host=replica_host,
    port=5432,
    dbname="databricks_postgres",
    user=db_user,
    password=cred.token,
    sslmode="require",
)
read_conn.autocommit = True

with read_conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM ecommerce.products")
    print(f"📖 Products (read from replica): {cur.fetchone()[0]}")

read_conn.close()

# COMMAND ----------

# MAGIC %md
# MAGIC > 💡 **DataCart pattern:** during the Spring Sale, route the storefront's product,
# MAGIC > ratings, and promotions reads to a replica endpoint, leaving the primary read-write
# MAGIC > endpoint free for cart and checkout writes. Because there is no automatic split, this
# MAGIC > is a deliberate choice in the app's connection configuration.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 2 — Connection Pooling (PgBouncer)
# MAGIC
# MAGIC Each Postgres server connection consumes memory, so a compute can only hold a limited
# MAGIC number of them. A busy app tier that opens a new connection per request will hit that
# MAGIC ceiling quickly. Lakebase ships with a **built-in PgBouncer pooler** that maintains a
# MAGIC pool of server connections and shares them across many client connections.
# MAGIC
# MAGIC **Key facts (from the docs):**
# MAGIC - Supports up to **10,000 concurrent client connections**.
# MAGIC - Runs in **transaction mode** — a server connection is held only for the duration of a
# MAGIC   single transaction, then returned to the pool.
# MAGIC - Pool size is roughly **90% of `max_connections`** (which varies by compute size);
# MAGIC   query timeout is **120 seconds**.
# MAGIC - Requires a **native Postgres password role** — OAuth roles are **not** supported on
# MAGIC   the pooler.
# MAGIC - Enable it from the Lakebase **Connect** dialog by selecting a password role and
# MAGIC   toggling the connection-pooling switch.

# COMMAND ----------

# MAGIC %md
# MAGIC ### Pooled vs. direct hostnames
# MAGIC
# MAGIC The pooler is exposed on a separate hostname. You choose pooled or direct simply by which
# MAGIC host you connect to (port `5432` either way):
# MAGIC
# MAGIC | Connection | Hostname pattern |
# MAGIC |------------|------------------|
# MAGIC | Read-write, **pooled** | `<endpoint-id>-pooler.<region>.<cloud>.databricks.com` |
# MAGIC | Read-only, **pooled** | `<endpoint-id>-ro-pooler.<region>.<cloud>.databricks.com` |
# MAGIC | Direct (unpooled) | the standard endpoint hostname (no `-pooler` suffix) |

# COMMAND ----------

# MAGIC %md
# MAGIC ### When to use the pooler vs. a direct connection
# MAGIC
# MAGIC Transaction mode is ideal for short, stateless queries (typical web/API traffic), but it
# MAGIC restricts features that rely on session state. Use a **direct connection** if you need:
# MAGIC
# MAGIC - SQL-level **prepared statements** or session-level settings
# MAGIC - **Temporary tables**
# MAGIC - `WITH HOLD` cursors
# MAGIC - **Advisory locks**
# MAGIC - `LISTEN` / `NOTIFY`
# MAGIC
# MAGIC > 💡 **DataCart pattern:** the storefront's high-volume, short-lived queries during the
# MAGIC > sale are a perfect fit for the pooled endpoint. Note that the DataCart app authenticates
# MAGIC > with short-lived **OAuth tokens** and pools connections *itself* (via `psycopg_pool`);
# MAGIC > to use the **built-in** PgBouncer pooler instead, connect through the `-pooler` host with
# MAGIC > a **password role**.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Goal | Feature | How |
# MAGIC |------|---------|-----|
# MAGIC | Scale **reads** | Read replicas | Add read-only endpoints (up to 6/branch); connect to the replica host explicitly |
# MAGIC | Scale **connections** | Built-in PgBouncer | Connect via the `-pooler` / `-ro-pooler` host using a password role |
# MAGIC
# MAGIC Both features build on Lakebase's compute/storage separation: replicas add read compute
# MAGIC without copying data, and the pooler adds connection capacity without a separate service
# MAGIC to run.
# MAGIC
# MAGIC > 📖 **Docs**: [Read replicas](https://docs.databricks.com/aws/en/oltp/projects/read-replicas) · [Connection pooling](https://docs.databricks.com/aws/en/oltp/projects/connection-pooling) · [Connect to your database](https://docs.databricks.com/aws/en/oltp/projects/connect)
