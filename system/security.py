import base64
import hashlib
import hmac
import os
import struct
import time
from urllib.parse import quote

from ldap3 import Connection, NONE, Server


TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6


def generate_totp_secret():
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def format_totp_secret(secret):
    compact = (secret or "").replace(" ", "").upper()
    return " ".join(compact[index:index + 4] for index in range(0, len(compact), 4))


def _decode_totp_secret(secret):
    compact = (secret or "").replace(" ", "").upper()
    padding = "=" * ((8 - len(compact) % 8) % 8)
    return base64.b32decode(compact + padding, casefold=True)


def generate_totp_token(secret, for_time=None):
    timestamp = int(for_time if for_time is not None else time.time())
    counter = timestamp // TOTP_STEP_SECONDS
    key = _decode_totp_secret(secret)
    message = struct.pack(">Q", counter)
    digest = hmac.new(key, message, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** TOTP_DIGITS)).zfill(TOTP_DIGITS)


def verify_totp_token(secret, code, window=1):
    normalized_code = "".join(char for char in str(code or "") if char.isdigit())

    if len(normalized_code) != TOTP_DIGITS:
        return False

    now = int(time.time())

    for offset in range(-window, window + 1):
        check_time = now + (offset * TOTP_STEP_SECONDS)

        if hmac.compare_digest(generate_totp_token(secret, check_time), normalized_code):
            return True

    return False


def build_totp_uri(user, secret, issuer="HelpDesk"):
    label = quote(f"{issuer}:{user.username}")
    issuer_value = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer_value}&digits={TOTP_DIGITS}&period={TOTP_STEP_SECONDS}"


def verify_directory_password(username, password):
    if not username or not password:
        return False

    server = Server(
        "ldap://cafelandia.pr.gov.br",
        get_info=NONE,
        connect_timeout=3
    )

    user = f"{username}@cafelandia.pr.gov.br"

    try:
        connection = Connection(
            server,
            user=user,
            password=password,
            receive_timeout=5
        )

        if connection.bind():
            connection.unbind()
            return True

    except Exception:
        return False

    return False


def verify_user_password(user, password):
    if not password:
        return False

    if user.has_usable_password() and user.check_password(password):
        return True

    return verify_directory_password(user.username, password)
