import os, base64, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

#key = os.urandom(32)
#base64.b64encode(key)

def encrypt(key_base64, message):
    """
    encrypt message
    key - base64
    message - normal
    """
    key = base64.b64decode(key_base64)
    iv = os.urandom(16)
    message_length = len(message)
    message = message + " " * (16 - len(message) % 16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(message.encode('utf-8')) + encryptor.finalize()
    return f"AES.MODE_CBC${base64.b64encode(iv).decode()}${message_length}${base64.b64encode(encrypted_data).decode()}"



def decrypt(key_base64, encrypted):
    """
    decrypt
    """
    algorithm, iv, binary_data_length, encrypted_data = encrypted.split("$")
    assert algorithm == "AES.MODE_CBC"
    iv = base64.b64decode(iv)
    encrypted_data = base64.b64decode(encrypted_data)
    key = base64.b64decode(key_base64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
    return decrypted_data[:int(binary_data_length)].decode('utf-8')


# keyBase64 = 'xxx'
# contents = {"a": "blehlbhe", "b": "11111asdasdasd", "c": "hehehahaa"}
# message = json.dumps(contents)
# encrypted = encrypt(keyBase64, message)

# print (encrypted)
# print ("------------------------------------")
# print (decrypt(keyBase64, encrypted))