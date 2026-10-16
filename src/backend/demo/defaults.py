"""Parameters that define how the demo site will be built."""

NB_OBJECTS = {"users": 4, "files": 50, "max_users_per_document": 4}

USERS = [
    {
        "email": "paige.turner@library.book",
        "full_name": "Paige Turner",
        "short_name": "Paige",
    },
    {
        "email": "miles.ahead@roadmap.fwd",
        "full_name": "Miles Ahead",
        "short_name": "Miles",
    },
    {
        "email": "archie.vist@vaulted.docs",
        "full_name": "Archie Vist",
        "short_name": "Archie",
    },
    {
        "email": "mark.down@plain.text",
        "full_name": "Mark Down",
        "short_name": "Mark",
    },
]

DEV_USERS = [
    {
        "username": "drive",
        "email": "drive@drive.world",
        "full_name": "Drive Developer",
        "short_name": "Drive",
        "language": "en-us",
    },
]

# Trees are (folders, files, depth): depth counts levels including files, and
# folders=0 makes each file a root item. Shared trees belong to an "org" user
# and add the role given to the persona. Shapes come from production stats.
PROFILES = {
    "median": {
        "owned": [(2, 6, 3)],
        "shared": [(0, 1, 1, "reader")],
        "link_traces": 2,
        "trash": 0,
    },
    "power": {
        "owned": [(600, 2000, 11)] + [(10, 40, 3)] * 10,
        "shared": [(10, 40, 4, "editor")] * 10,
        "link_traces": 133,
        "trash": 52,
    },
    "biggest_shared": {
        "owned": [],
        "shared": [
            (15000, 45000, 16, "editor"),
            (3000, 10000, 12, "reader"),
            (885, 3578, 8, "editor"),
        ],
        "link_traces": 0,
        "trash": 0,
    },
    "biggest_owner": {
        "owned": [(12000, 45000, 15)] + [(112, 625, 6)] * 16,
        "shared": [],
        "link_traces": 0,
        "trash": 0,
    },
    "deepest": {
        "owned": [(12000, 8000, 24)],
        "shared": [],
        "link_traces": 0,
        "trash": 0,
    },
    "flat": {
        "owned": [(0, 825, 1)],
        "shared": [],
        "link_traces": 0,
        "trash": 0,
    },
    "big_folder": {
        "owned": [(1, 5000, 2)],
        "shared": [],
        "link_traces": 0,
        "trash": 0,
    },
    "most_shared": {
        "owned": [(1, 150, 2)],
        "shared": [(0, 150, 1, "reader")],
        "link_traces": 0,
        "trash": 0,
    },
    "history": {
        "owned": [(10, 990, 3)],
        "shared": [],
        "link_traces": 3400,
        "trash": 800,
    },
}

# (mimetype, extension, weight, median size in bytes) from production stats.
PROFILE_MIMETYPES = [
    ("application/pdf", "pdf", 1168, 190_000),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
        328,
        190_000,
    ),
    ("image/jpeg", "jpg", 323, 550_000),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx", 167, 190_000),
    ("image/png", "png", 143, 550_000),
    ("application/vnd.oasis.opendocument.text", "odt", 104, 190_000),
    ("text/plain", "txt", 96, 3_000),
    (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pptx",
        75,
        190_000,
    ),
    ("application/msword", "doc", 69, 190_000),
    ("application/vnd.oasis.opendocument.spreadsheet", "ods", 43, 190_000),
    ("text/csv", "csv", 34, 3_000),
    ("application/vnd.ms-excel", "xls", 33, 190_000),
    ("application/octet-stream", "bin", 28, 190_000),
    ("image/tiff", "tiff", 28, 550_000),
    ("video/mp4", "mp4", 27, 39_000_000),
    ("audio/mpeg", "mp3", 16, 1_000_000),
]
