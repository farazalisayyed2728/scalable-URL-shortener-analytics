import secrets
import string

# 62 alphanumeric characters (case-sensitive)
BASE62_ALPHABET = string.ascii_letters + string.digits


def generate_random_code(length: int = 7) -> str:
    """
    Generates a cryptographically secure random Base62 string.
    Using secrets.choice() rather than random.choice() to eliminate predictability.
    """
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))