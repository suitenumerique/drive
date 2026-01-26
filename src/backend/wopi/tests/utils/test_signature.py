"""Tests for the signature utils."""

from base64 import b64encode
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from wopi.utils import signature

# ---------- TESTS FOR ticks_to_datetime ----------


def test_ticks_to_datetime():
    """Test the ticks_to_datetime function."""
    # Test epoch (.NET ticks = 0)
    assert signature.ticks_to_datetime(0) == datetime(1, 1, 1, 0, 0, 0, 0, timezone.utc)

    # Test Unix epoch (.NET ticks for 1970-01-01)
    assert signature.ticks_to_datetime(621355968000000000) == datetime(
        1970, 1, 1, 0, 0, 0, 0, timezone.utc
    )

    # Test a specific date (2024-01-01 00:00:00 UTC)
    # Calculate ticks for 2024-01-01
    expected_2024 = datetime(2024, 1, 1, 0, 0, 0, 0, timezone.utc)
    unix_timestamp_2024 = expected_2024.timestamp()
    dotnet_epoch_ticks = 621355968000000000
    ticks_per_second = 10000000
    ticks_2024 = int(dotnet_epoch_ticks + (unix_timestamp_2024 * ticks_per_second))
    assert signature.ticks_to_datetime(ticks_2024) == expected_2024

    # Test with fractional seconds
    # Add 1234567 ticks = 123456700 nanoseconds = 123.4567 milliseconds
    ticks_with_fraction = 621355968000000000 + 1234567
    result = signature.ticks_to_datetime(ticks_with_fraction)
    assert result.year == 1970
    assert result.month == 1
    assert result.day == 1
    # 1234567 ticks = 123456700 nanoseconds = 123456.7 microseconds
    # Round to nearest microsecond = 123457 microseconds
    assert result.microsecond == 123457


# ---------- TESTS FOR build_expected_proof ----------


def test_build_expected_proof():
    """Test the build_expected_proof function."""
    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000

    result = signature.build_expected_proof(access_token, url, timestamp)

    # Verify structure: [len(token)] [token] [len(url)] [url] [len(timestamp)] [timestamp]
    token_bytes = access_token.encode("utf-8")
    url_bytes = url.upper().encode("utf-8")  # URL is uppercased
    timestamp_bytes = signature.encode_timestamp(timestamp)

    expected = (
        signature.encode_number(len(token_bytes))
        + token_bytes
        + signature.encode_number(len(url_bytes))
        + url_bytes
        + signature.encode_number(len(timestamp_bytes))
        + timestamp_bytes
    )

    assert result == expected


def test_build_expected_proof_url_uppercase():
    """Test that build_expected_proof uppercases the URL."""
    access_token = "token"
    url_lower = "https://example.com/test"
    url_upper = "HTTPS://EXAMPLE.COM/TEST"
    timestamp = 1000000

    result_lower = signature.build_expected_proof(access_token, url_lower, timestamp)
    result_upper = signature.build_expected_proof(access_token, url_upper, timestamp)

    # Both should produce the same result
    assert result_lower == result_upper


def test_build_expected_proof_empty_strings():
    """Test build_expected_proof with empty strings."""
    access_token = ""
    url = ""
    timestamp = 0

    result = signature.build_expected_proof(access_token, url, timestamp)

    # Should still have proper structure with length prefixes
    assert len(result) == 4 + 0 + 4 + 0 + 4 + 8  # Three length prefixes + timestamp


def test_build_expected_proof_unicode():
    """Test build_expected_proof with unicode characters."""
    access_token = "tëst_tökën"
    url = "https://example.com/test/path"
    timestamp = 621355968000000000

    result = signature.build_expected_proof(access_token, url, timestamp)

    # Should handle unicode correctly
    assert len(result) > 0
    assert access_token.encode("utf-8") in result


# ---------- TESTS FOR verify_wopi_proof ----------


def _generate_rsa_keypair():
    """Generate an RSA key pair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    public_key = private_key.public_key()
    return private_key, public_key


def _serialize_public_key(public_key):
    """Serialize RSA public key to PEM format."""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _sign_data(private_key, data):
    """Sign data with RSA private key using PKCS#1 v1.5 padding and SHA256."""
    signature_bytes = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return b64encode(signature_bytes).decode("utf-8")


def test_verify_wopi_proof_valid_signature():
    """Test verify_wopi_proof with a valid signature."""
    private_key, public_key = _generate_rsa_keypair()
    public_key_pem = _serialize_public_key(public_key)

    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    signature_value = _sign_data(private_key, expected_proof)

    proof_keys = {"public_key": public_key_pem}

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=signature_value,
        signature_old=None,
        expected_proof=expected_proof,
    )

    assert result is True


def test_verify_wopi_proof_invalid_signature():
    """Test verify_wopi_proof with an invalid signature."""
    private_key, public_key = _generate_rsa_keypair()
    public_key_pem = _serialize_public_key(public_key)

    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    # Create invalid signature (sign different data)
    wrong_proof = signature.build_expected_proof("wrong_token", url, timestamp)
    signature_value = _sign_data(private_key, wrong_proof)

    proof_keys = {"public_key": public_key_pem}

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=signature_value,
        signature_old=None,
        expected_proof=expected_proof,
    )

    assert result is False


def test_verify_wopi_proof_with_signature_old_valid():
    """Test verify_wopi_proof when signature_old is valid with current key."""
    private_key, public_key = _generate_rsa_keypair()
    public_key_pem = _serialize_public_key(public_key)

    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    # Invalid current signature
    invalid_signature = b64encode(b"invalid_signature").decode("utf-8")

    # Valid old signature
    signature_old = _sign_data(private_key, expected_proof)

    proof_keys = {"public_key": public_key_pem}

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=invalid_signature,
        signature_old=signature_old,
        expected_proof=expected_proof,
    )

    assert result is True


def test_verify_wopi_proof_with_old_public_key():
    """Test verify_wopi_proof when signature is valid with old public key."""
    # Generate two key pairs (current and old)
    old_private_key, old_public_key = _generate_rsa_keypair()
    _, current_public_key = _generate_rsa_keypair()

    old_public_key_pem = _serialize_public_key(old_public_key)
    current_public_key_pem = _serialize_public_key(current_public_key)

    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    # Sign with old private key (simulating key rotation scenario)
    signature_value = _sign_data(old_private_key, expected_proof)

    proof_keys = {
        "public_key": current_public_key_pem,
        "old_public_key": old_public_key_pem,
    }

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=signature_value,
        signature_old=None,
        expected_proof=expected_proof,
    )

    assert result is True


def test_verify_wopi_proof_all_invalid():
    """Test verify_wopi_proof when all signatures are invalid."""
    _, public_key = _generate_rsa_keypair()
    _, old_public_key = _generate_rsa_keypair()
    public_key_pem = _serialize_public_key(public_key)
    old_public_key_pem = _serialize_public_key(old_public_key)

    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    # All invalid signatures
    invalid_signature = b64encode(b"invalid_signature").decode("utf-8")
    invalid_signature_old = b64encode(b"invalid_signature_old").decode("utf-8")

    proof_keys = {
        "public_key": public_key_pem,
        "old_public_key": old_public_key_pem,
    }

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=invalid_signature,
        signature_old=invalid_signature_old,
        expected_proof=expected_proof,
    )

    assert result is False


def test_verify_wopi_proof_wrong_key():
    """Test verify_wopi_proof when signature is signed with a different key."""
    # Generate two different key pairs
    private_key1, _ = _generate_rsa_keypair()
    _, public_key2 = _generate_rsa_keypair()

    # Sign with key1 but verify with key2
    access_token = "test_token"
    url = "https://example.com/wopi/files/123"
    timestamp = 621355968000000000
    expected_proof = signature.build_expected_proof(access_token, url, timestamp)

    signature_value = _sign_data(private_key1, expected_proof)

    proof_keys = {"public_key": _serialize_public_key(public_key2)}

    result = signature.verify_wopi_proof(
        proof_keys=proof_keys,
        signature=signature_value,
        signature_old=None,
        expected_proof=expected_proof,
    )

    assert result is False
