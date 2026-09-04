import base64
import datetime
import hashlib
import math
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from password_validator import PasswordValidator

from src.config import config
from src.exceptions import InvalidDateError


def pagination(total: int, page: int, limit: int) -> Dict[str, Any]:
    total_pages = math.ceil(total / limit)
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None

    return {
        "page": page,
        "limit": limit,
        "prevPage": prev_page,
        "nextPage": next_page,
        "totalPage": total_pages,
    }


def pagination_aggregate(page: int, limit: int) -> Dict[str, Any]:
    skip = limit * (page - 1)
    return {
        "metadata": [
            {"$count": "totalData"},
            {
                "$project": {
                    "totalData": 1,
                    "totalPage": {
                        "$toInt": {"$ceil": {"$divide": ["$totalData", limit]}}
                    },
                    "previousPage": {
                        "$cond": {
                            "if": {"$lte": [page, 1]},
                            "then": None,
                            "else": {"$subtract": [page, 1]},
                        }
                    },
                    "currentPage": {
                        "$cond": {
                            "if": {"$eq": [page, 1]},
                            "then": 1,
                            "else": {"$toInt": {"$ceil": {"$divide": [page, 1]}}},
                        }
                    },
                    "nextPage": {
                        "$cond": {
                            "if": {
                                "$lte": [
                                    {"$add": [page, 1]},
                                    {
                                        "$toInt": {
                                            "$ceil": {"$divide": ["$totalData", limit]}
                                        }
                                    },
                                ]
                            },
                            "then": {"$add": [page, 1]},
                            "else": None,
                        }
                    },
                }
            },
        ],
        "data": [{"$skip": skip}, {"$limit": limit}],
    }


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_fernet() -> Fernet:
    """Generate a Fernet key using the SECRET_KEY from config."""
    secret = config.secret_key
    key_bytes = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def fernet_encrypt_value(value: Optional[str]) -> Optional[str]:
    """Encrypt a string using Fernet and the app's SECRET_KEY."""
    if not value:
        return value
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def fernet_decrypt_value(encrypted_value: Optional[str]) -> Optional[str]:
    """Decrypt a string using Fernet and the app's SECRET_KEY."""
    if not encrypted_value:
        return encrypted_value
    f = _get_fernet()
    try:
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        # If decryption fails, it might not be encrypted or key changed
        return encrypted_value


def validate_password_strength(password: str) -> bool:
    """
    Validate password strength:
    - Min 8 chars, Max 64 chars
    - At least one uppercase
    - At least one lowercase
    - At least one digit
    - At least one symbol
    - No spaces
    """
    password_rules = PasswordValidator()
    password_rules.min(8).max(
        64
    ).has().uppercase().has().lowercase().has().digits().has().symbols().no().spaces()
    return password_rules.validate(password)


def cleanse_image_url(url: Optional[str]) -> Optional[str]:
    """Keep remote image URLs as-is (storage layer removed)."""
    return url


def parse_date_range(start_date: Optional[str], end_date: Optional[str]):
    """
    Parses start_date and end_date strings (YYYY-MM-DD) into datetime objects.
    Raises InvalidDateError if format is invalid.
    """
    parsed_start = None
    parsed_end = None
    if start_date:
        try:
            parsed_start = datetime.datetime.strptime(start_date, "%Y-%m-%d").replace(
                tzinfo=datetime.timezone.utc
            )
        except ValueError:
            raise InvalidDateError()
    if end_date:
        try:
            parsed_end = datetime.datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=datetime.timezone.utc
            )
        except ValueError:
            raise InvalidDateError()
    return parsed_start, parsed_end
