import base64
import os

key = base64.urlsafe_b64encode(os.urandom(32)).decode()

with open(".env", "a") as f:
    f.write(f"FERNET_KEY={key}\n")

print(f"Appended FERNET_KEY to .env: {key}")
