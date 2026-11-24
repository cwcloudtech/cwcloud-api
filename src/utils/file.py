import os
import time
import base64

from utils.logger import log_msg

def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        log_msg("DEBUG", "[create_dir_if_not_exists] path {} doesn't exists, creating...".format(path))
        os.makedirs(path)

def quiet_remove(path):
    try:
        os.remove(path)
    except FileNotFoundError as e:
        log_msg("WARN", "[quiet_remove] file {} doesn't exists".format(path))

def read_file_content(path):
    with open(path) as file:
        return file.read()

def create_cert_locally(file_name, file_content):
    with open(f"{file_name}.pem" , "w") as file:
        file.write(file_content)

    time.sleep(1)

def delete_cert_locally(file_name):
    quiet_remove(f"{file_name}.pem")

def get_b64_content(file_name: str, remove: bool):
    b64_content = ""
    with open(file_name, "rb") as file:
        log_msg("DEBUG", f"[get_b64_content] writing file {file_name} content in response")
        b64_content = base64.b64encode(file.read()).decode()
        file.close()

    if remove:
        log_msg("DEBUG", f"[get_b64_content] trying to delete {file_name}")
        quiet_remove(file_name)

    return b64_content
