import hashlib
from uuid import uuid4


def generate_uuid() -> str:
    return uuid4().hex


def generate_hash(value: str) -> str:
    hash_obj = hashlib.sha256(value.encode())
    return hash_obj.hexdigest()
