"""
Utils for validating WOPI proof signatures.

https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/scenarios/proofkey
"""

import struct
from base64 import b64decode
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

# ---------- HELPERS ----------

# .NET DateTime epoch: January 1, 0001 00:00:00
# Unix datetime epoch: January 1, 1970 00:00:00 UTC
# Ticks between these epochs: 621,355,968,000,000,000
DOTNET_EPOCH_TICKS = 621355968000000000

# Each tick is 100 nanoseconds = 0.0000001 seconds
TICKS_PER_SECOND = 10000000


def ticks_to_datetime(ticks: int) -> datetime:
    """Convert a .NET DateTime ticks to a datetime object.

    .NET DateTime ticks represent the number of 100-nanosecond intervals
    since January 1, 0001 00:00:00.000 in the Gregorian calendar.

    Args:
        ticks: Integer representing .NET DateTime ticks

    Returns:
        datetime: Python datetime object corresponding to the ticks
    """

    # Convert .NET ticks to Unix timestamp (seconds since 1970-01-01)
    unix_seconds = (ticks - DOTNET_EPOCH_TICKS) / TICKS_PER_SECOND

    # Create datetime from Unix timestamp (UTC)
    return datetime.fromtimestamp(unix_seconds, timezone.utc)


# ---------- BYTE ENCODING (C# equivalent) ----------


def encode_number(n: int) -> bytes:
    """Encode a number as a 4-byte big endian."""
    return struct.pack(">I", n)


def encode_timestamp(ts: int) -> bytes:
    """
    Encode a timestamp as a 8-byte big endian.
    A timestamp from the wopi header is a .NET DateTime ticks
    https://learn.microsoft.com/fr-fr/dotnet/api/system.datetime.ticks
    """
    return struct.pack(">Q", ts)


# ---------- BUILD EXPECTED PROOF ----------


def build_expected_proof(access_token: str, url: str, timestamp: int) -> bytes:
    """
    Build the expected proof for a WOPI request.

    https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/scenarios/proofkeys#constructing-the-expected-proof
    """
    access_token_bytes = access_token.encode("utf-8")
    url_bytes = url.upper().encode("utf-8")
    timestamp_bytes = encode_timestamp(timestamp)

    proof = bytearray()
    proof.extend(encode_number(len(access_token_bytes)))
    proof.extend(access_token_bytes)
    proof.extend(encode_number(len(url_bytes)))
    proof.extend(url_bytes)
    proof.extend(encode_number(len(timestamp_bytes)))
    proof.extend(timestamp_bytes)

    return bytes(proof)


# ---------- RSA SIGNATURE VERIFICATION ----------


def verify_wopi_proof(
    proof_keys: dict[str, bytes],
    signature: str,
    signature_old: str | None,
    expected_proof: bytes,
) -> bool:
    """
    Verify the RSA-SHA256 signature for a WOPI singature using PKCS#1 v1.5 padding.

    https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/online/scenarios/proofkeys#verifying-the-proof-keys
    """

    public_key = serialization.load_pem_public_key(proof_keys["public_key"])
    old_public_key = None
    if proof_keys.get("old_public_key"):
        old_public_key = serialization.load_pem_public_key(proof_keys["old_public_key"])

    signed_proof = b64decode(signature)

    # Frist try if the current signature is valid with the current public key
    try:
        public_key.verify(
            signed_proof,
            expected_proof,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        pass

    # Then try if the signature old value is valid using the current public key
    if signature_old:
        signed_proof_old = b64decode(signature_old)
        try:
            public_key.verify(
                signed_proof_old,
                expected_proof,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            pass

    # Finally try he X-WOPI-Proof value using the old public key
    if old_public_key:
        try:
            old_public_key.verify(
                signed_proof,
                expected_proof,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            pass

    return False
