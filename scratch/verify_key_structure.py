import json
from cryptography.hazmat.primitives import serialization

with open("firebase-service-account.json") as f:
    data = json.load(f)

private_key_str = data["private_key"]
print("Key starts with:", private_key_str[:50])
print("Key ends with:", private_key_str[-50:])

try:
    key = serialization.load_pem_private_key(
        private_key_str.encode("utf-8"),
        password=None
    )
    print("PEM parsed successfully!")
    print("Key type:", type(key))
    print("Key size (bits):", key.key_size)
except Exception as e:
    print("Error parsing PEM private key:")
    print(e)
