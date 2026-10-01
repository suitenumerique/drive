# Scaling

Drive stores items as a tree in an ltree `path` column. On a large instance the
item table holds millions of rows. A query that is fast on a development database
can take seconds there, so changes to item queries should be checked on data
shaped like production.

## Checking the performance of a change

### Generate a production sized dataset

The `create_perf_dataset` command fills an empty database with a dataset shaped
like production. By default it creates 50k users and 4M items spread over deep
trees, with accesses, link traces, favorites and trashed items. Rows are
generated with SQL and no file is written to the object storage. It takes about
15 minutes.

```bash
make perf-dataset FLUSH_ARGS=--noinput
```

This flushes the database first. The volumes can be changed with the command
options (`--users`, `--items`, `--accesses`, `--link-traces`,
`--max-favorites-per-user`, `--deleted-ratio`):

```bash
docker compose run --rm app-dev python manage.py create_perf_dataset --items 1000000
```

The development user (`drive@drive.world`) gets a small drive, with a few shares
received and a link trace. This is useful to check the experience of a user with
few items on a large instance.

### Profile the endpoints

The `profile_endpoints` command calls the main item and user endpoints as a given
user. It reports:
- the time of each call;
- the number of queries of the last call;
- the slowest queries;
- with `--explain`, the execution plan of the slowest query of each endpoint.

```bash
# As the development user, with the plans of the slowest queries
docker compose exec app-dev python manage.py profile_endpoints --no-jit --explain

# As another user, only on some endpoints
docker compose exec app-dev python manage.py profile_endpoints --no-jit \
    --user-id <user id> --only list --only recents
```

Good practices:
- **Profile at least two users.** A light one, like the development user, and a
  heavy one with thousands of accesses and link traces. They reveal different
  problems: a light user exposes costs that grow with the size of the tables, a
  heavy user exposes costs that grow with their own collection.
- **Compare before and after the change** with the same command, the same users
  and the same dataset. The first call of each endpoint warms up the caches, so
  compare the following ones.
- **Read the plans, not only the timings.** Watch for sequential scans on
  `drive_item`, index lookups repeated once per row (`loops=…`), and row estimates
  far from the actual rows.
- **Watch the number of queries.** It should not grow with the number of items
  returned.

## JIT on production databases

Postgres can compile queries to machine code with JIT (just-in-time
compilation). It is on by default. Postgres decides to compile a query from its
**estimated** cost (`jit_above_cost`, `jit_inline_above_cost`,
`jit_optimize_above_cost`), and compiles it again on every execution.

This suits long analytical queries, not a web application running many short
queries. On Drive, compiling some item queries took longer than running them:
listing the children of a folder spent up to 1.8s compiling a query that ran in
about 15ms. Queries whose estimated cost is high, but whose actual cost is low,
are compiled on every call.

We recommend disabling JIT for the role or the database used by Drive:

```sql
ALTER ROLE <drive user> SET jit = off;
-- or
ALTER DATABASE <drive database> SET jit = off;
```

- The setting applies to new connections, so restart the application or recycle
  its connection pool.
- Disabling it for the role keeps JIT available for other roles, such as
  reporting.
- To measure the time spent compiling before changing anything, look at the
  `jit_*_time` columns of `pg_stat_statements` (PostgreSQL 15 and later), or at
  the `JIT:` section of an `EXPLAIN (ANALYZE)`.

Use `--no-jit` with `profile_endpoints` to measure in the same conditions.

## Btree and GiST indexes on paths

The `path` column has two indexes:
- **a unique btree index**, which supports `<`, `<=`, `=`, `>=` and `>`;
- **a GiST index**, which supports the same operators plus the ltree tree and
  pattern operators: `@>` (is an ancestor of), `<@` (is a descendant of), `~`,
  `@` and `?`.

django_ltree's `path__descendants` and `path__ancestors` lookups use `<@` and
`@>`, so only the GiST index can serve them. On millions of paths made of UUIDs,
a GiST search is much slower than a btree lookup: around a millisecond against a
few microseconds. Postgres also estimates these operators poorly, which can lead
it to a bad plan. It barely shows on a single query, but it adds up quickly in
correlated subqueries and annotations, which run once per listed item.

In queries that run on every request or for every item, prefer the helpers in
`core/models.py`, which rely on the btree index or on the item ids:
- `path__in_subtree=X` matches `X` and its descendants, like
  `path__descendants=X`, as a range of the btree index.
- `IdInSubtrees` matches the items under many roots at once.
- `IdInPath` matches an item and its ancestors from the ids in a path, instead of
  `__ancestors`.

These helpers rely on each path being made of the ids of the item's ancestors
and its own id. The GiST index remains the right tool for pattern queries and
occasional tree queries.
