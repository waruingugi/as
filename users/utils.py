from random_username.generate import generate_username

from users.constants import MAX_USERNAME_LEN, MIN_USERNAME_LEN
from users.models import User


def username_generator(
    minimum_length=MIN_USERNAME_LEN, max_length=MAX_USERNAME_LEN
) -> str:
    """Generate default username."""
    username = generate_username(1)[0]
    while (
        len(username) > max_length
        or len(username) < minimum_length
        or User.objects.filter(username=username).exists()
    ):
        username = generate_username(1)[0]

    return username
