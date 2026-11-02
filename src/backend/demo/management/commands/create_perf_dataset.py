"""create_perf_dataset management command"""

# SQL statements only interpolate module constants, values are passed as parameters
# ruff: noqa: S608

import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from core import models

from demo import defaults
from demo.management.commands.create_demo import Timeit, get_or_create_demo_user

FIRST_NAMES = [
    "alice", "bruno", "camille", "david", "emma", "fabien", "gabriel", "helene",
    "ines", "julien", "karim", "laura", "mathieu", "nadia", "olivier", "pauline",
    "quentin", "rachel", "sophie", "thomas", "ugo", "valerie", "william", "yasmine",
    "zoe", "antoine", "beatrice", "cedric", "delphine", "etienne", "florence",
    "guillaume", "isabelle", "jerome", "lucie", "maxime", "nicolas", "oceane",
]  # fmt: skip
LAST_NAMES = [
    "martin", "bernard", "dubois", "thomas", "robert", "richard", "petit",
    "durand", "leroy", "moreau", "simon", "laurent", "lefebvre", "michel",
    "garcia", "david", "bertrand", "roux", "vincent", "fournier", "morel",
    "girard", "andre", "lefevre", "mercier", "dupont", "lambert", "bonnet",
    "francois", "martinez", "legrand", "garnier", "faure", "rousseau", "blanc",
]  # fmt: skip
DOMAINS = [
    "agriculture.test", "culture.test", "defense.test", "ecologie.test",
    "education.test", "finances.test", "interieur.test", "justice.test",
    "sante.test", "travail.test", "numerique.test", "region-est.test",
]  # fmt: skip
FOLDER_TITLES = [
    "Projets", "Archives", "Comptes rendus", "Budget", "Ressources humaines",
    "Communication", "Juridique", "Marchés publics", "Réunions", "Partage",
    "Photos", "Rapports", "Documentation", "Formations", "Courriers",
]  # fmt: skip
FILE_KINDS = [
    ("Rapport", "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ("Tableau", "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (
        "Présentation",
        "pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    ("Note", "pdf", "application/pdf"),
    ("Photo", "png", "image/png"),
    ("Scan", "jpg", "image/jpeg"),
    ("Vidéo", "mp4", "video/mp4"),
    ("Export", "csv", "text/csv"),
    ("Archive", "zip", "application/zip"),
]  # fmt: skip

# Share of the non-root items created at each depth, starting at depth 2.
LEVEL_SHARES = [0.30, 0.25, 0.18, 0.12, 0.08, 0.04, 0.03]
# Share of the accesses that are owner accesses on root items, the rest are shares.
ROOT_ACCESS_RATIO = 0.7
ROOT_FOLDER_RATIO = 0.6
FOLDER_RATIO = 0.12
# Pareto shape of the number of children per folder: lower means more skewed
CHILDREN_PARETO_ALPHA = 1.3
MAX_CHILDREN_PER_FOLDER = 20000

# Pick a random element of the array passed as the given SQL parameter
RANDOM_ELEMENT = "(%({name})s::text[])[1 + floor(random() * cardinality(%({name})s::text[]))::int]"

# Columns shared by root and child items. The `c` relation must expose
# `id`, `creator_id`, `is_folder`, `kind` and `created_at`.
ITEM_COLUMNS = """
    id, path, created_at, updated_at, title, link_reach, link_role, creator_id,
    deleted_at, ancestors_deleted_at, hard_deleted_at, filename, type, upload_state,
    mimetype, main_workspace, size, quota_excluded, description,
    malware_detection_info, target_id
"""
ITEM_VALUES = f"""
    c.id,
    {{path}},
    c.created_at,
    c.created_at + random() * (now() - c.created_at),
    CASE WHEN c.is_folder
        THEN {RANDOM_ELEMENT.format(name="folder_titles")} || ' ' || (1 + floor(random() * 50))::int
        ELSE (%(file_titles)s::text[])[c.kind] || ' ' || (1 + floor(random() * 1000))::int
            || '.' || (%(file_extensions)s::text[])[c.kind]
    END,
    {{link_reach}},
    'reader',
    c.creator_id,
    NULL, NULL, NULL,
    CASE WHEN c.is_folder THEN NULL
        ELSE 'file-' || (1 + floor(random() * 1000))::int || '.' || (%(file_extensions)s::text[])[c.kind]
    END,
    CASE WHEN c.is_folder THEN 'folder' ELSE 'file' END,
    CASE WHEN c.is_folder THEN NULL ELSE 'ready' END,
    CASE WHEN c.is_folder THEN NULL ELSE (%(file_mimetypes)s::text[])[c.kind] END,
    false,
    CASE WHEN c.is_folder THEN NULL ELSE floor(power(random(), 3) * 50000000)::bigint END,
    false,
    NULL,
    '{{{{}}}}'::jsonb,
    NULL
"""
ROOT_LINK_REACH = """
    CASE WHEN random() < 0.9 THEN 'restricted'
        WHEN random() < 0.7 THEN 'authenticated' ELSE 'public' END
"""
CHILD_LINK_REACH = """
    CASE WHEN random() < 0.95 THEN NULL
        WHEN random() < 0.8 THEN 'authenticated' ELSE 'public' END
"""
# Pick a random active user, skewed so that a few users get most of the rows
SKEWED_USER = "u.ids[1 + floor(power(random(), {power}) * cardinality(u.ids))::int]"
ACTIVE_USER_IDS = (
    "(SELECT array_agg(id ORDER BY created_at) AS ids FROM drive_user WHERE is_active)"
)


# Parameters available to every statement
SQL_PARAMS = {
    "folder_titles": FOLDER_TITLES,
    "file_titles": [kind[0] for kind in FILE_KINDS],
    "file_extensions": [kind[1] for kind in FILE_KINDS],
    "file_mimetypes": [kind[2] for kind in FILE_KINDS],
}


class Command(BaseCommand):
    """
    Fill an empty database with a dataset shaped like production, to reproduce
    and measure slow queries locally. Rows are generated with set-based SQL and
    no file is written to the object storage.
    """

    help = __doc__

    def add_arguments(self, parser):
        """Add arguments to size the dataset, defaults match production volumes."""
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            default=False,
            help="Force command execution despite DEBUG is set to False",
        )
        parser.add_argument("--users", type=int, default=50_000)
        parser.add_argument("--items", type=int, default=4_000_000)
        parser.add_argument("--accesses", type=int, default=140_000)
        parser.add_argument("--link-traces", type=int, default=50_000)
        parser.add_argument("--max-favorites-per-user", type=int, default=10)
        parser.add_argument("--deleted-ratio", type=float, default=0.02)

    def handle(self, *args, **options):
        """Handling of the management command."""
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                (
                    "This command is not meant to be used in production environment "
                    "except you know what you are doing, if so use --force parameter"
                )
            )
        if models.Item.objects.exists():
            raise CommandError("The database must not contain items, run `make resetdb` first.")

        nb_roots = max(1, int(options["accesses"] * ROOT_ACCESS_RATIO))

        with Timeit(self.stdout, "Creating users"):
            self.create_users(options["users"])

        # Postgres DDL is transactional: indexes come back if the generation fails
        with transaction.atomic():
            index_definitions = self.drop_item_indexes()
            with Timeit(self.stdout, "Creating root items"):
                self.create_roots(nb_roots)
            nb_remaining = options["items"] - nb_roots
            for depth, share in enumerate(LEVEL_SHARES, start=2):
                with Timeit(self.stdout, f"Creating items at depth {depth}"):
                    created = self.create_children(depth, int(nb_remaining * share))
                if not created:
                    break
            with Timeit(self.stdout, "Recreating item indexes"):
                # Run the deferred foreign key checks, Postgres refuses to create
                # an index on a table with pending trigger events
                self.execute_sql("SET CONSTRAINTS ALL IMMEDIATE")
                for definition in index_definitions:
                    self.execute_sql(definition.replace("%", "%%"))

        with Timeit(self.stdout, "Creating accesses"):
            self.create_accesses(max(0, options["accesses"] - nb_roots))

        with Timeit(self.stdout, "Moving items to the trash"):
            self.trash_items(options["deleted_ratio"])

        with Timeit(self.stdout, "Creating link traces"):
            self.create_link_traces(options["link_traces"])

        with Timeit(self.stdout, "Creating favorites"):
            self.create_favorites(options["max_favorites_per_user"])

        with Timeit(self.stdout, "Creating development user"):
            self.create_dev_user()

        with Timeit(self.stdout, "Analyzing tables"):
            self.analyze()

        self.stdout.write(
            f"Created {models.User.objects.count()} users, "
            f"{models.Item.objects.count()} items, "
            f"{models.ItemAccess.objects.count()} accesses, "
            f"{models.LinkTrace.objects.count()} link traces, "
            f"{models.ItemFavorite.objects.count()} favorites."
        )

    def execute_sql(self, sql, params=None):
        """Execute a SQL statement and return the number of rows it affected."""
        with connection.cursor() as cursor:
            cursor.execute(sql, {**SQL_PARAMS, **(params or {})})
            return cursor.rowcount

    def drop_item_indexes(self):
        """
        Drop the item indexes that are not backing a constraint and return their
        definitions, to recreate them after the bulk insert: maintaining a GiST
        index row by row is much slower than building it once.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexrelid::regclass::text, pg_get_indexdef(indexrelid)
                FROM pg_index
                WHERE indrelid = 'drive_item'::regclass
                AND NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conindid = indexrelid)
                """
            )
            indexes = cursor.fetchall()
            for name, _definition in indexes:
                cursor.execute(f'DROP INDEX "{name}"')
        return [definition for _name, definition in indexes]

    def create_users(self, nb_users):
        """Create active users with realistic and varied emails."""
        self.execute_sql(
            f"""
            INSERT INTO drive_user (
                id, password, is_superuser, created_at, updated_at, sub, full_name,
                short_name, email, timezone, is_device, is_staff, is_active, claims
            )
            SELECT
                gen_random_uuid(), '!', false, s.created_at, s.created_at,
                'perf-user-' || s.n, initcap(s.first_name) || ' ' || initcap(s.last_name),
                initcap(s.first_name),
                s.first_name || '.' || s.last_name
                    || CASE WHEN random() < 0.3 THEN s.n::text ELSE '' END
                    || '@' || s.domain,
                %(timezone)s, false, false, random() < 0.95, '{{}}'::jsonb
            FROM (
                SELECT
                    n,
                    now() - random() * interval '730 days' AS created_at,
                    {RANDOM_ELEMENT.format(name="first_names")} AS first_name,
                    {RANDOM_ELEMENT.format(name="last_names")} AS last_name,
                    {RANDOM_ELEMENT.format(name="domains")} AS domain
                FROM generate_series(1, %(nb_users)s) AS n
            ) s
            """,
            {
                "nb_users": nb_users,
                "timezone": settings.TIME_ZONE,
                "first_names": FIRST_NAMES,
                "last_names": LAST_NAMES,
                "domains": DOMAINS,
            },
        )

    def create_roots(self, nb_roots):
        """Create root items, each owned by its creator through an owner access."""
        values = ITEM_VALUES.format(path="c.id::text::ltree", link_reach=ROOT_LINK_REACH)
        self.execute_sql(
            f"""
            INSERT INTO drive_item ({ITEM_COLUMNS})
            SELECT {values}
            FROM (
                SELECT
                    gen_random_uuid() AS id,
                    {SKEWED_USER.format(power=2)} AS creator_id,
                    random() < %(root_folder_ratio)s AS is_folder,
                    1 + floor(random() * %(nb_kinds)s)::int AS kind,
                    now() - random() * interval '730 days' AS created_at
                FROM generate_series(1, %(nb_roots)s), {ACTIVE_USER_IDS} u
            ) c
            """,
            {
                "nb_roots": nb_roots,
                "root_folder_ratio": ROOT_FOLDER_RATIO,
                "nb_kinds": len(FILE_KINDS),
            },
        )
        self.execute_sql(
            """
            INSERT INTO drive_item_access (id, created_at, updated_at, team, role, item_id, user_id)
            SELECT gen_random_uuid(), created_at, created_at, '', 'owner', id, creator_id
            FROM drive_item
            """
        )

    def create_children(self, depth, nb_items):
        """
        Create about `nb_items` children for the folders at the parent depth. The
        number of children per folder follows a Pareto distribution so that most
        folders are small while a few of them are huge.
        """
        is_last_level = depth == len(LEVEL_SHARES) + 1
        values = ITEM_VALUES.format(
            path="(c.parent_path::text || '.' || c.id::text)::ltree",
            link_reach=CHILD_LINK_REACH,
        )
        return self.execute_sql(
            f"""
            WITH parents AS (
                SELECT path, creator_id, power(1 - random(), -1.0 / %(alpha)s) AS weight
                FROM drive_item
                WHERE type = 'folder' AND nlevel(path) = %(parent_depth)s
            ),
            sized AS (
                SELECT path, creator_id, LEAST(
                    %(max_children)s,
                    floor(%(nb_items)s * weight / sum(weight) OVER () + random())
                )::int AS nb_children
                FROM parents
            )
            INSERT INTO drive_item ({ITEM_COLUMNS})
            SELECT {values}
            FROM (
                SELECT
                    gen_random_uuid() AS id,
                    s.path AS parent_path,
                    s.creator_id,
                    random() < %(folder_ratio)s AS is_folder,
                    1 + floor(random() * %(nb_kinds)s)::int AS kind,
                    now() - random() * interval '730 days' AS created_at
                FROM sized s CROSS JOIN LATERAL generate_series(1, s.nb_children)
            ) c
            """,
            {
                "alpha": CHILDREN_PARETO_ALPHA,
                "parent_depth": depth - 1,
                "max_children": MAX_CHILDREN_PER_FOLDER,
                "nb_items": nb_items,
                "folder_ratio": 0 if is_last_level else FOLDER_RATIO,
                "nb_kinds": len(FILE_KINDS),
            },
        )

    def create_accesses(self, nb_accesses):
        """Share random items at any depth with random users."""
        self.execute_sql(
            f"""
            INSERT INTO drive_item_access (id, created_at, updated_at, team, role, item_id, user_id)
            SELECT gen_random_uuid(), now(), now(), '', s.role, s.item_id, s.user_id
            FROM (
                SELECT
                    i.id AS item_id,
                    i.creator_id,
                    {SKEWED_USER.format(power=3)} AS user_id,
                    CASE WHEN random() < 0.5 THEN 'reader'
                        WHEN random() < 0.7 THEN 'editor'
                        WHEN random() < 0.66 THEN 'administrator'
                        ELSE 'owner' END AS role
                FROM (
                    SELECT id, creator_id FROM drive_item
                    WHERE nlevel(path) > 1 ORDER BY random() LIMIT %(nb_accesses)s
                ) i, {ACTIVE_USER_IDS} u
            ) s
            WHERE s.user_id <> s.creator_id
            ON CONFLICT DO NOTHING
            """,
            {"nb_accesses": nb_accesses},
        )

    def trash_items(self, ratio):
        """Soft delete random files, as leaves they have no descendant to update."""
        self.execute_sql(
            """
            WITH trashed AS (
                SELECT id, now() - random() * make_interval(days => %(cutoff_days)s) AS deleted_at
                FROM drive_item
                WHERE type = 'file' AND random() < %(ratio)s
            )
            UPDATE drive_item SET
                deleted_at = trashed.deleted_at,
                ancestors_deleted_at = trashed.deleted_at
            FROM trashed
            WHERE drive_item.id = trashed.id
            """,
            {"ratio": ratio, "cutoff_days": settings.TRASHBIN_CUTOFF_DAYS},
        )

    def create_link_traces(self, nb_link_traces):
        """Trace visits of random users on items reachable by link."""
        self.execute_sql(
            f"""
            INSERT INTO drive_link_trace (id, created_at, updated_at, item_id, user_id)
            SELECT gen_random_uuid(), now(), now(), s.item_id, s.user_id
            FROM (
                SELECT i.id AS item_id, i.creator_id, {SKEWED_USER.format(power=2)} AS user_id
                FROM (
                    SELECT id, creator_id FROM drive_item
                    WHERE link_reach IN ('authenticated', 'public') AND deleted_at IS NULL
                    ORDER BY random() LIMIT %(nb_link_traces)s
                ) i, {ACTIVE_USER_IDS} u
            ) s
            WHERE s.user_id <> s.creator_id
            ON CONFLICT DO NOTHING
            """,
            {"nb_link_traces": nb_link_traces},
        )

    def create_favorites(self, max_per_user):
        """
        Give each user a few favorites among the items they created or that were
        shared with them, most users have 5 favorites or less.
        """
        self.execute_sql(
            """
            INSERT INTO drive_item_favorite (id, created_at, updated_at, item_id, user_id)
            SELECT gen_random_uuid(), now(), now(), f.item_id, u.id
            FROM (
                SELECT id, floor(power(random(), 2) * (%(max_per_user)s + 1))::int AS nb
                FROM drive_user WHERE is_active
            ) u
            CROSS JOIN LATERAL (
                SELECT candidates.item_id FROM (
                    SELECT id AS item_id FROM drive_item
                    WHERE creator_id = u.id AND deleted_at IS NULL
                    UNION
                    SELECT item_id FROM drive_item_access WHERE user_id = u.id
                ) candidates
                ORDER BY random() LIMIT u.nb
            ) f
            """,
            {"max_per_user": max_per_user},
        )

    def create_dev_user(self):
        """
        Give the development user a small drive, with a few shares, a link trace
        and a favorite, to reproduce slow requests for a user with few items.
        """
        user = get_or_create_demo_user(defaults.DEV_USERS[0])

        root = models.Item.objects.create(
            title="Mes documents",
            type=models.ItemTypeChoices.FOLDER,
            creator=user,
            link_reach=models.LinkReachChoices.RESTRICTED,
        )
        models.ItemAccess.objects.create(item=root, user=user, role=models.RoleChoices.OWNER)
        for index, (title, extension, mimetype) in enumerate(FILE_KINDS * 2):
            item_id = uuid.uuid4()
            models.Item.objects.create(
                id=item_id,
                path=f"{root.path!s}.{item_id!s}",
                title=f"{title} {index}.{extension}",
                filename=f"{title.lower()}-{index}.{extension}",
                mimetype=mimetype,
                size=1024 * (index + 1),
                type=models.ItemTypeChoices.FILE,
                creator=user,
            )
        models.Item.objects.filter(creator=user, type=models.ItemTypeChoices.FILE).update(
            upload_state=models.ItemUploadStateChoices.READY
        )

        shared_folders = models.Item.objects.filter(
            type=models.ItemTypeChoices.FOLDER, path__depth=1, deleted_at__isnull=True
        ).exclude(creator=user)[:2]
        for folder in shared_folders:
            models.ItemAccess.objects.create(item=folder, user=user, role=models.RoleChoices.EDITOR)

        traced_item = (
            models.Item.objects.filter(
                link_reach=models.LinkReachChoices.AUTHENTICATED, deleted_at__isnull=True
            )
            .exclude(creator=user)
            .exclude(accesses__user=user)
            .first()
        )
        if traced_item:
            models.LinkTrace.objects.create(item=traced_item, user=user)

        models.ItemFavorite.objects.create(
            item=models.Item.objects.filter(creator=user, type=models.ItemTypeChoices.FILE).first(),
            user=user,
        )

    def analyze(self):
        """Refresh the planner statistics, vacuuming when outside of a transaction."""
        # A parallel vacuum needs more shared memory than the 64MB docker gives by default
        command = "ANALYZE" if connection.in_atomic_block else "VACUUM (ANALYZE, PARALLEL 0)"
        for table in (
            "drive_user",
            "drive_item",
            "drive_item_access",
            "drive_link_trace",
            "drive_item_favorite",
        ):
            self.execute_sql(f"{command} {table}")
