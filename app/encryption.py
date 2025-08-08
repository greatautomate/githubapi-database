from cryptography.fernet import Fernet
from app.config import Config
import base64

def get_cipher():
    key = Config.ENCRYPTION_KEY.encode()
    # Ensure key is proper length for Fernet
    key = base64.urlsafe_b64encode(key.ljust(32)[:32])
    return Fernet(key)

def encrypt_token(token: str) -> str:
    cipher = get_cipher()
    encrypted = cipher.encrypt(token.encode())
    return base64.b64encode(encrypted).decode()

def decrypt_token(encrypted_token: str) -> str:
    cipher = get_cipher()
    encrypted_bytes = base64.b64decode(encrypted_token.encode())
    decrypted = cipher.decrypt(encrypted_bytes)
    return decrypted.decode()
