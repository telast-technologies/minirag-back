from uuid import uuid4


def UUIDGenerator(prefix: str) -> str:
    """
    Generates a unique identifier with a given prefix.

    Args:
        prefix (str): The prefix to prepend to the generated UUID.

    Returns:
        str: A unique identifier string.
    """
    return f"{prefix}_{uuid4().hex}"
