import hashlib
from db import get_user_by_email

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(email, password):
    user = get_user_by_email(email)
    if user:
        if user[3] == hash_password(password):
            return user
    return None
