from pwdlib import PasswordHash


class HashingService:
    """
    Service for password hashing and verification.

    Uses a modern recommended password hashing configuration.
    """

    def __init__(self):
        self.password_hash = PasswordHash.recommended()

    def decode(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password (str): Plain text password to verify.
            hashed_password (str): Hashed password to compare against.

        Returns:
            bool: True if password matches, False otherwise.
        """
        return self.password_hash.verify(plain_password, hashed_password)

    def encode(self, password: str) -> str:
        """
        Hash a password.

        Args:
            password (str): Plain text password to hash.

        Returns:
            str: Hashed password.
        """
        return self.password_hash.hash(password)


hasher = HashingService()
