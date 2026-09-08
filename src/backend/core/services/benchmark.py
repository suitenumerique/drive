"""Query benchmark scenarios for the benchmark management command.

Historical mode preserves restricted_2 scenarios and timing instrumentation.
Both modes now run with isolated application settings; protocol versions differ
from pytest-era runs, which must not be treated as identical measurements.
"""

import hashlib
import json
import platform
import shutil
import statistics
import subprocess
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from rest_framework.test import APIClient

from core import models
from core.services.item_exports import export_descendants

PROFILES = {
    "smoke": (20, 60, 20, 3, 4, 10, 5, 10),
    "big": (100, 500, 100, 3, 5, 20, 50, 5),
    "xl": (100, 5000, 1500, 8, 20, 100, 50, 3),
    "xxl": (200, 10000, 5000, 10, 25, 100, 50, 3),
}


def require(condition, message="Invalid benchmark response"):
    """Abort invalid measurements even when Python assertions are disabled."""
    if not condition:
        raise CommandError(message)


class Benchmark:  # pylint: disable=too-many-instance-attributes,too-many-arguments
    """Run query scenarios against an already isolated and migrated database."""

    def __init__(self, *, mode, profile, reps, restrictions, output, commit=None):  # noqa: PLR0913
        self.mode = mode
        self.profile = "xxl" if profile == "large" else profile
        (
            self.page_size,
            self.nb_children,
            self.nb_subtrees,
            self.subtree_depth,
            self.nb_files,
            self.nb_redundant_users,
            self.nb_abilities_sample,
            historical_reps,
        ) = PROFILES[self.profile]
        self.reps = reps if reps is not None else historical_reps if mode == "historical" else 10
        self.with_restrictions = restrictions
        self.output = output
        self.commit = commit
        self.folder = models.ItemTypeChoices.FOLDER
        self.file = models.ItemTypeChoices.FILE
        self.restriction = getattr(models.ItemTypeChoices, "RESTRICTION", None)
        self.restricted_every = 10
        self.config = {
            name: getattr(self, name)
            for name in (
                "profile",
                "reps",
                "page_size",
                "nb_children",
                "nb_subtrees",
                "subtree_depth",
                "nb_files",
                "with_restrictions",
                "restricted_every",
                "nb_redundant_users",
                "nb_abilities_sample",
            )
        }

    # pylint: disable=too-many-locals,too-many-statements
    def build_dataset(self):  # noqa: PLR0915 - explicit benchmark topology and access setup
        """Build a deterministic tree, sized by the volume knobs above.

        Items are inserted with bulk_create (paths computed by hand): the factories
        go through create_child whose per-insert unique-title check scans siblings,
        which is quadratic under a single parent and intractable at large volumes.
        """

        def bench_user(name):
            user, _ = models.User.objects.get_or_create(
                sub=f"bench-{name}",
                defaults={
                    "email": f"{name}@bench.local",
                    "full_name": name.capitalize(),
                    "language": "en-us",
                    "password": make_password(None),
                },
            )
            return user

        sequence = 0

        def next_id():
            nonlocal sequence
            if self.mode == "historical":
                return uuid.uuid4()
            sequence += 1
            return uuid.uuid5(uuid.NAMESPACE_URL, f"drive-benchmark/{sequence}")

        alice = bench_user("alice")
        bob = bench_user("bob")
        carol = bench_user("carol")

        workspace_id = next_id()
        workspace = models.Item.objects.create(
            id=workspace_id,
            path=str(workspace_id),
            title="bench-ws",
            type=self.folder,
            creator=alice,
        )
        models.ItemAccess.objects.create(item=workspace, user=alice, role=models.RoleChoices.OWNER)
        models.ItemAccess.objects.create(item=workspace, user=bob, role=models.RoleChoices.EDITOR)

        def new_item(title, parent_path, type_, **kwargs):
            pk = next_id()
            return models.Item(
                id=pk,
                title=title,
                creator=alice,
                type=type_,
                path=f"{parent_path}.{pk}" if parent_path else str(pk),
                link_reach=models.LinkReachChoices.RESTRICTED,
                **kwargs,
            )

        def new_restricted(title, parent_path):
            """Return (root folder, restriction under parent_path targeting it)."""
            folder = new_item(title, None, self.folder)
            restriction = new_item(title, parent_path, self.restriction, target=folder)
            return folder, restriction

        restricted_indices = (
            set(range(5, self.nb_children, self.restricted_every))
            if self.with_restrictions
            else set()
        )

        items = []
        restrictions = []
        folders = []
        for i in range(self.nb_children):
            if i in restricted_indices:
                folder, restriction = new_restricted(f"folder-{i:04d}", workspace.path)
                restrictions.append(restriction)
            else:
                folder = new_item(f"folder-{i:04d}", workspace.path, self.folder)
            folders.append(folder)
            items.append(folder)

        deep_restricted = None
        for i in range(self.nb_subtrees):
            node = folders[i % self.nb_children]
            for depth in range(self.subtree_depth):
                if self.with_restrictions and i == 2 and depth == 0:
                    node, restriction = new_restricted(f"sub-{i:04d}-{depth}", node.path)
                    restrictions.append(restriction)
                    deep_restricted = node
                else:
                    node = new_item(f"sub-{i:04d}-{depth}", node.path, self.folder)
                items.append(node)
                if depth == 0:
                    for j in range(self.nb_files):
                        items.append(
                            new_item(
                                f"file-{i:04d}-{j}",
                                node.path,
                                self.file,
                                filename="file.txt",
                                upload_state=models.ItemUploadStateChoices.READY,
                            )
                        )

        models.Item.objects.bulk_create(items, batch_size=2000)
        models.Item.objects.bulk_create(restrictions, batch_size=2000)

        restricted = [folders[i] for i in sorted(restricted_indices)]
        accesses = [
            models.ItemAccess(item=item, user=carol, role=models.RoleChoices.OWNER)
            for item in restricted + ([deep_restricted] if deep_restricted else [])
        ]

        # Redundant users for the deactivate scenario
        redundant_users = [bench_user(f"redundant{i}") for i in range(self.nb_redundant_users)]
        accesses.extend(
            models.ItemAccess(item=workspace, user=user, role=models.RoleChoices.EDITOR)
            for user in redundant_users
        )
        reader = None
        if self.mode == "pghero":
            # Dense direct shares exercise COUNT(DISTINCT accesses), in addition to inheritance.
            accesses.extend(
                models.ItemAccess(item=folder, user=user, role=models.RoleChoices.READER)
                for folder in folders[: min(500, self.nb_children)]
                for user in redundant_users[:10]
            )
            reader = bench_user("reader")
            accesses.extend(
                models.ItemAccess(item=folder, user=reader, role=models.RoleChoices.READER)
                for folder in folders[::2]
            )
            models.ItemAccess.objects.bulk_create(accesses, batch_size=2000)
            # Link-only access, disjoint from reader's explicit shares.
            traced = folders[1::4]
            models.Item.objects.filter(pk__in=[item.pk for item in traced]).update(
                link_reach=models.LinkReachChoices.AUTHENTICATED
            )
            models.LinkTrace.objects.bulk_create(
                [models.LinkTrace(item=item, user=reader) for item in traced], batch_size=2000
            )
            models.ItemFavorite.objects.bulk_create(
                [models.ItemFavorite(item=item, user=bob) for item in folders[::10]],
                batch_size=2000,
            )
        else:
            models.ItemAccess.objects.bulk_create(accesses, batch_size=2000)

        return {
            "reader": reader,
            "alice": alice,
            "bob": bob,
            "carol": carol,
            "workspace": workspace,
            "folders": folders,
            "restricted": restricted,
            "redundant_users": redundant_users,
        }

    def timing_summary(self, samples):
        """Keep raw samples as well as robust summary statistics."""
        return {
            "median_ms": round(statistics.median(samples), 3),
            "min_ms": round(min(samples), 3),
            "max_ms": round(max(samples), 3),
            "samples_ms": [round(value, 3) for value in samples],
        }

    def measure(self, fn):
        """Separate normal API execution from SQL profiling overhead."""
        expected = fn()  # Warm application and database caches.
        samples = []
        for _ in range(self.reps):
            start = time.perf_counter()
            actual = fn()
            samples.append((time.perf_counter() - start) * 1000)
            require(actual == expected, "Response IDs/count changed between repetitions")

        statements = defaultdict(list)

        def capture(execute, sql, params, many, context):
            start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                statements[sql].append((time.perf_counter() - start) * 1000)

        with connection.execute_wrapper(capture):
            require(fn() == expected, "Response IDs/count changed during SQL profiling")
        sql_results = [
            {
                "sql": sql,
                "calls": len(times),
                "total_ms": round(sum(times), 3),
                **self.timing_summary(times),
            }
            for sql, times in statements.items()
        ]
        sql_results.sort(key=lambda entry: entry["total_ms"], reverse=True)
        return {
            "api": self.timing_summary(samples),
            "rows": len(expected[0]),
            "count": expected[1],
            "sql_calls": sum(len(times) for times in statements.values()),
            "sql_execute_ms": round(sum(sum(times) for times in statements.values()), 3),
            "sql": sql_results,
        }

    def run_pghero(self, data, result):
        """Exercise folder listings and accessible-root selection on one fixed dataset."""
        clients = {}
        for role in ("alice", "bob", "reader"):
            clients[role] = APIClient()
            clients[role].force_authenticate(data[role])

        def run(name, role, url, params):
            def request():
                response = clients[role].get(url, params)
                require(response.status_code == 200, f"API returned {response.status_code}")
                payload = response.json()
                rows = payload["results"]
                require(rows, f"Empty benchmark scenario: {name}")
                require(len(rows) <= self.page_size, "Page size exceeded")
                return tuple(row["id"] for row in rows), payload.get("count")

            stats = self.measure(request)
            result["scenarios"][name] = stats
            print(  # noqa: T201 - benchmark CLI output
                f"{name:35s} API={stats['api']['median_ms']:9.2f}ms "
                f"SQL={stats['sql_execute_ms']:9.2f}ms queries={stats['sql_calls']}",
                flush=True,
            )

        children_url = f"/api/v1.0/items/{data['workspace'].pk}/children/"
        for role in ("alice", "bob"):
            for ordering in ("-type,title", "created_at"):
                run(
                    f"children_{role}_{ordering}",
                    role,
                    children_url,
                    {"page_size": self.page_size, "ordering": ordering},
                )
        run(
            "children_second_page",
            "bob",
            children_url,
            {"page_size": self.page_size, "page": 2, "ordering": "-type,title"},
        )
        # Exercise a deeper folder with both files and a nested folder.
        nested = models.Item.objects.get(title="sub-0000-0")
        run(
            "nested_children",
            "bob",
            f"/api/v1.0/items/{nested.pk}/children/",
            {"page_size": self.page_size, "ordering": "-type,title"},
        )
        run("accessible_roots", "reader", "/api/v1.0/items/", {"page_size": self.page_size})
        run("accessible_roots_bob", "bob", "/api/v1.0/items/", {"page_size": self.page_size})
        run(
            "shared_roots",
            "reader",
            "/api/v1.0/items/",
            {"page_size": self.page_size, "is_creator_me": "false"},
        )
        run(
            "search_title",
            "bob",
            "/api/v1.0/items/search/",
            {"page_size": self.page_size, "title": "folder"},
        )

    def measure_historical(self, fn, setup=None, reps=None):
        """Run fn `reps` times, return query count and timing stats."""
        reps = self.reps if reps is None else reps
        if setup:
            setup()
        fn()  # warmup (caches, connection)
        times, queries = [], []
        for _ in range(reps):
            if setup:
                setup()
            start = time.perf_counter()
            with CaptureQueriesContext(connection) as ctx:
                fn()
            times.append((time.perf_counter() - start) * 1000)
            queries.append(len(ctx))
        return {
            "queries": max(queries),
            "ms_median": round(statistics.median(times), 1),
            "ms_min": round(min(times), 1),
        }

    def run_historical(self, data, results):
        """Preserve restricted_2 authentication, capture overhead and scenario order."""
        extra = {}

        def scenario(name, fn, setup=None):
            results["scenarios"][name] = self.measure_historical(fn, setup=setup)

        workspace = data["workspace"]

        # --- children list, as workspace owner
        client = APIClient()
        client.force_login(data["alice"])

        def children_owner():
            response = client.get(
                f"/api/v1.0/items/{workspace.id!s}/children/?page_size={self.page_size}"
            )
            require(response.status_code == 200, f"API returned {response.status_code}")
            extra["children_owner_rows"] = len(response.json()["results"])

        scenario("children_list_owner", children_owner)

        # --- children list, as editor
        client_bob = APIClient()
        client_bob.force_login(data["bob"])

        def children_editor():
            response = client_bob.get(
                f"/api/v1.0/items/{workspace.id!s}/children/?page_size={self.page_size}"
            )
            require(response.status_code == 200, f"API returned {response.status_code}")
            extra["children_editor_rows"] = len(response.json()["results"])

        scenario("children_list_editor", children_editor)

        # --- search by title, as editor
        def search_title():
            response = client_bob.get("/api/v1.0/items/search/?title=folder")
            require(response.status_code == 200, f"API returned {response.status_code}")
            payload = response.json()
            extra["search_rows"] = len(payload if isinstance(payload, list) else payload["results"])

        scenario("search_title", search_title)

        # --- export descendants iteration, as editor
        def export():
            folder = models.Item.objects.get(pk=workspace.pk)
            entries = list(export_descendants(folder))
            extra["export_rows"] = len(entries)

        scenario("export_descendants", export)

        if self.with_restrictions:
            restricted_ids = [item.pk for item in data["restricted"][: self.nb_abilities_sample]]

            # --- get_abilities loop over restricted folders, as container owner (no access)
            def abilities_container_owner():
                for item in models.Item.objects.filter(pk__in=restricted_ids):
                    item.get_abilities(data["alice"])

            scenario("abilities_restricted_container_owner", abilities_container_owner)

            # --- same loop, as editor of the workspace (no access to restricted content)
            def abilities_editor():
                for item in models.Item.objects.filter(pk__in=restricted_ids):
                    item.get_abilities(data["bob"])

            scenario("abilities_restricted_editor", abilities_editor)

            # --- unrestrict on a folder with redundant accesses
            target = data["folders"][50]
            models.ItemAccess.objects.get_or_create(
                item=target, user=data["carol"], defaults={"role": models.RoleChoices.OWNER}
            )

            def deactivate_setup():
                target.refresh_from_db()
                if not target.is_restricted:
                    target.restrict(data["carol"])
                for user in data["redundant_users"]:
                    models.ItemAccess.objects.get_or_create(
                        item=target, user=user, defaults={"role": models.RoleChoices.EDITOR}
                    )

            def deactivate():
                target.refresh_from_db()
                target.unrestrict()

            scenario("unrestrict", deactivate, setup=deactivate_setup)

        results["extra"] = extra

    def git_metadata(self):
        """Use explicit host metadata when .git is not mounted in Docker."""
        revision = self.commit
        dirty = None
        git_binary = shutil.which("git")
        if not revision and git_binary:
            try:
                revision = subprocess.check_output(  # noqa: S603 - fixed Git arguments, no shell
                    [git_binary, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
                ).strip()
                dirty = bool(
                    subprocess.check_output(  # noqa: S603 - fixed Git arguments, no shell
                        [git_binary, "status", "--porcelain", "--untracked-files=no"],
                        stderr=subprocess.DEVNULL,
                        text=True,
                    ).strip()
                )
            except (OSError, subprocess.CalledProcessError):
                revision = None
        return {
            "commit": revision,
            "tracked_dirty": dirty,
            "benchmark_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }

    def run(self):
        """Run the selected protocol without changing the application queries."""
        require(connection.vendor == "postgresql", "This benchmark requires PostgreSQL/ltree")
        require(
            not self.with_restrictions or self.restriction is not None, "Restrictions unavailable"
        )
        started = time.perf_counter()
        data = self.build_dataset()
        with connection.cursor() as cursor:
            if self.mode == "pghero":
                for model in (
                    models.Item,
                    models.ItemAccess,
                    models.LinkTrace,
                    models.ItemFavorite,
                    models.User,
                ):
                    table = connection.ops.quote_name(model._meta.db_table)  # noqa: SLF001
                    cursor.execute(f"ANALYZE {table}")
            cursor.execute("SELECT version()")
            postgres_version = cursor.fetchone()[0]
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename = 'drive_item' ORDER BY indexname"
            )
            indexes = [{"name": name, "definition": definition} for name, definition in cursor]
        result = {
            "schema_version": 2,
            "mode": self.mode,
            "protocol_version": "restricted_2-command-v1"
            if self.mode == "historical"
            else "pghero-command-v1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "config": self.config,
            "has_restricted": self.with_restrictions,
            "source": self.git_metadata(),
            "python": platform.python_version(),
            "postgres": postgres_version,
            "item_indexes": indexes,
            "cache_backend": settings.CACHES["default"]["BACKEND"],
            "dataset_items": models.Item.objects.count(),
            "dataset_accesses": models.ItemAccess.objects.count(),
            "setup_seconds": round(time.perf_counter() - started, 3),
            "scenarios": {},
        }
        if self.mode == "historical":
            self.run_historical(data, result)
        else:
            self.run_pghero(data, result)
        output = self.output
        output.parent.mkdir(parents=True, exist_ok=True)
        # Never silently replace an existing baseline, even with an explicit path.
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
        return result
