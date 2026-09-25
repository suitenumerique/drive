# Query benchmarks

Run from the repository root:

```bash
bin/manage benchmark --mode pghero --profile smoke
bin/manage benchmark --mode historical --profile big --restrictions
```

The command creates a uniquely named PostgreSQL database, runs migrations, measures
requests and drops that database on success or failure. The configured database
is not populated. The database user needs `CREATE DATABASE` permission. A forced
process kill can leave the temporary database behind; its name is printed at startup.

Requests use local caches, email and entitlement backends with external search
disabled. The workload runs in a rolled-back transaction so background jobs
registered with `on_commit` do not run.

## Options

| Option | Default | Description |
|---|---|---|
| `--mode` | `pghero` | `pghero` or `historical` |
| `--profile` | `smoke` | `smoke`, `big`, `xl`, `xxl`; `large` aliases `xxl` |
| `--reps` | Mode-dependent | At least 2 repetitions after warmup |
| `--restrictions` | Disabled | Include restricted folders |
| `--output` | `bench_results/bench_<mode>_<timestamp>.json` | New file; existing files are never overwritten |
| `--commit` | Detected with Git, otherwise unknown | Revision represented by the measurements |

Paths are relative to the command's working directory. With `bin/manage`, the
container runs in `/app`, mounted from `src/backend`, so default results appear
in `src/backend/bench_results` on the host.

```bash
bin/manage benchmark --mode pghero --profile xxl --reps 10 \
  --restrictions --commit "$(git rev-parse HEAD)"
```

The old `DRIVE_BENCH_*` environment variables are no longer used.

## Modes

`pghero` measures eleven scenarios: folder listings as owner and editor with two
sort orders, a second page, nested children, accessible roots for a user with
many shares and for a user with one inherited share, shared roots, the
breadcrumb of a deep item and search.
It records API wall times, then profiles SQL in a separate pass. The fixture
contains direct shares, link traces and favorites; `ANALYZE` runs before
measurement.

`historical` retains the `restricted_2` fixture, scenarios, session authentication
and timing instrumentation. It measures listings, search and export, plus abilities
and lifting a restriction when restrictions are enabled. Timing includes SQL
capture overhead. It does not run an explicit `ANALYZE`.

Command results use new protocol versions because isolation settings and fixture
creation differ from the former pytest runner. Neither mode recreates the older
boolean restriction implementation.

| Profile | Direct folders | Nested chains | Chain depth | Files per chain | Page size |
|---|---:|---:|---:|---:|---:|
| smoke | 60 | 20 | 3 | 4 | 20 |
| big | 500 | 100 | 3 | 5 | 100 |
| xl | 5,000 | 1,500 | 8 | 20 | 100 |
| xxl | 10,000 | 5,000 | 10 | 25 | 200 |
| 3xl | 20,000 | 25,000 | 20 | 20 | 200 |

Files sit in the first folder of each chain. PgHero mode defaults to 10 repetitions;
historical mode uses 10, 5, 3, 3 and 3 respectively. The 3xl profile exceeds one
million items: its dataset is built in memory before the bulk inserts, and the
run needs several gigabytes of RAM.

## Browse the dataset

```bash
bin/manage create_demo --bench big --bench-role reader
```

Builds the `pghero` dataset, with restrictions, in the configured database and
copies the accesses and link traces of one bench user (`alice`, `bob` or
`reader`, default `bob`) to the development users. Files have no content in
object storage. Run `make resetdb` before building it again.

## Compare

```bash
python3 bin/compare_bench.py before.json after.json
```

Use identical modes, profiles, repetitions and restriction settings on the same
machine. The report shows the median and the minimum of the API samples: the
minimum is less sensitive to other processes running on the machine. The
comparator labels missing metadata as provisional and differing
protocols/configurations as incompatible. Its exit status is 0 for compatible
metadata, 1 for incompatible or provisional comparisons, and 2 for invalid
input.

## Before and after a change

The command only exists on this branch, so measuring an older revision means
running it against that revision's application code with the same instrument:
copy the harness into a worktree of the revision to measure.

```bash
# 1. Measure the branch (after)
bin/manage benchmark --profile xxl --reps 10 --restrictions --output after.json

# 2. Measure the base revision (before), with the branch's instrument
git worktree add ../drive-before origin/main
cp src/backend/core/services/benchmark.py ../drive-before/src/backend/core/services/
cp src/backend/core/management/commands/benchmark.py \
   ../drive-before/src/backend/core/management/commands/
(cd ../drive-before && bin/manage benchmark --profile xxl --reps 10 \
   --restrictions --output "$OLDPWD/before.json")
git worktree remove ../drive-before

# 3. Compare
python3 bin/compare_bench.py before.json after.json
```

The harness files must stay identical on both sides: never measure a revision
with its own copy of the instrument. The `source.commit` field of each result
records which revision was measured, and `tracked_dirty` flags a worktree where
tracked files differ from that revision. Run the two measurements close
together on an idle machine, and distrust wall-time deltas of a few
milliseconds: read the per-statement SQL profile of the JSON for anything that
small.
