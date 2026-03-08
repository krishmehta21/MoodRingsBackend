import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# We need a stable key for the database encryption.
# In a real scenario, this is securely injected. 
# Providing a fallback valid Fernet key if not present in env.
_key = os.getenv("ENCRYPTION_KEY", b'F-Z3kH4L58fJc-_K6x-tN_E_mR9wX_1yN3Z1O-aVf2c=')
_cipher_suite = Fernet(_key)

def encrypt_text(text: str) -> str:
    if not text:
        return text
    return _cipher_suite.encrypt(text.encode('utf-8')).decode('utf-8')

def decrypt_text(encrypted_text: str) -> str:
    if not encrypted_text:
        return encrypted_text
    try:
        return _cipher_suite.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
    except Exception:
        return encrypted_text # Fallback if already decrypted or invalid
