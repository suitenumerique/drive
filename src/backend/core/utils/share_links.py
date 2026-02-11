"""Share link token helpers (deterministic, no DB writes).

Share tokens are deterministic and unforgeable (HMAC) so we can:
- expose stable share URLs without storing per-item tokens
- validate share access without leaking item existence/metadata
"""

from __future__ import annotations

from uuid import UUID

from django.utils.crypto import constant_time_compare, salted_hmac

_SIG_HEX_LEN = 32  # 128-bit truncated signature (hex)
_HMAC_SALT = "drive.share_link.v1"


def compute_item_share_token(item_id: UUID) -> str:
    """Compute a stable share token for an item UUID."""
    item_id_str = str(item_id)
    sig = salted_hmac(_HMAC_SALT, item_id_str).hexdigest()[:_SIG_HEX_LEN]
    return f"{item_id_str}.{sig}"


def validate_item_share_token(token: str) -> UUID | None:
    """Validate a share token and return the embedded item UUID (or None)."""
    if not token:
        return None

    try:
        item_id_raw, sig = token.rsplit(".", 1)
        item_id = UUID(item_id_raw)
    except ValueError:
        return None

    expected = salted_hmac(_HMAC_SALT, str(item_id)).hexdigest()[:_SIG_HEX_LEN]
    if not constant_time_compare(sig, expected):
        return None

    return item_id
