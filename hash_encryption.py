import hashlib
import os

class HashEncryption:
    def __init__(self, salt_length=16):
        self.salt_length = salt_length

    def generate_salt(self):
        """Generate a random salt."""
        return os.urandom(self.salt_length)

    def hash_password(self, password, salt=None):

        if salt is None:
            salt = self.generate_salt()

        # Combine the salt and password
        password_salt_combo = salt + password.encode()

        # Hash the combination using SHA-256
        hashed = hashlib.sha256(password_salt_combo).digest()
        return salt, hashed

    def verify_password(self, password, salt, hashed_password):
        _, new_hashed = self.hash_password(password, salt)
        return hashed_password == new_hashed
