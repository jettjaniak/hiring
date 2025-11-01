"""
Encryption and decryption utilities using Fernet (symmetric encryption)
"""
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Canary value for key verification
CANARY_VALUE = "HIRING_PROCESS_KEY_V1_2024"


class EncryptionManager:
    def __init__(self, key: str):
        """
        Initialize with encryption key (password/passphrase).
        Derives a Fernet key from the password.
        """
        # Use PBKDF2 to derive a key from the password
        # In production, salt should be stored and consistent
        salt = b'hiring-process-salt-v1'  # Fixed salt for demo
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = kdf.derive(key.encode())
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        self.cipher = Fernet(fernet_key)

    def encrypt_string(self, plaintext: str) -> bytes:
        """Encrypt a string and return bytes"""
        return self.cipher.encrypt(plaintext.encode())

    def decrypt_string(self, ciphertext: bytes) -> str:
        """Decrypt bytes and return string"""
        return self.cipher.decrypt(ciphertext).decode()

    def encrypt_json(self, data: dict) -> bytes:
        """Encrypt a JSON object and return bytes"""
        json_str = json.dumps(data, sort_keys=True)
        return self.encrypt_string(json_str)

    def decrypt_json(self, ciphertext: bytes) -> dict:
        """Decrypt bytes and return JSON object"""
        json_str = self.decrypt_string(ciphertext)
        return json.loads(json_str)

    def create_canary(self) -> bytes:
        """Create an encrypted canary for key verification"""
        return self.encrypt_string(CANARY_VALUE)

    def verify_canary(self, encrypted_canary: bytes) -> bool:
        """Verify that the encrypted canary decrypts to the expected value"""
        try:
            decrypted = self.decrypt_string(encrypted_canary)
            return decrypted == CANARY_VALUE
        except Exception:
            return False

    @staticmethod
    def generate_key() -> str:
        """Generate a new random encryption key"""
        return base64.urlsafe_b64encode(Fernet.generate_key()).decode()
