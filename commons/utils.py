from hashlib import md5, sha256
from uuid import uuid4


def md5_hash(value: str) -> str:
    """Convert string value into hash"""
    return md5(value.encode()).hexdigest()


def generate_uuid() -> str:
    return uuid4().hex


def generate_hash(value: str) -> str:
    hash_obj = sha256(value.encode())
    return hash_obj.hexdigest()
