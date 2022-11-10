import base64
import json
import logging
import os
import subprocess
from pathlib import Path
from shlex import quote

import requests

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)


store_url = "https://store.pollinations.ai"


def execute_shell(cmd):
    return subprocess.check_output(cmd, shell=True).decode("utf-8")


def encode_file(local_path):
    with open(local_path, "rb") as f:
        encoded_file = base64.b64encode(f.read()).decode("utf-8")
    return f"data:text/plain;base64,{encoded_file}"


def upload_file(local_path: str) -> str:
    """Uploads a file to pollinations store and returns the url"""
    local_path = Path(local_path)
    request = {local_path.name: encode_file(local_path)}
    response = requests.post(f"{store_url}/", json=request)
    response.raise_for_status()
    cid = response.text
    json_data_url = f"{store_url}/ipfs/{cid}"
    response = requests.get(json_data_url).json()
    return response[local_path.name]


def encode_referenced_files(request):
    if isinstance(request, Path):
        if os.path.exists(request):
            return encode_file(request)
        else:
            return request
    elif isinstance(request, dict):
        return {key: encode_referenced_files(value) for key, value in request.items()}
    elif isinstance(request, list):
        return [encode_referenced_files(value) for value in request]
    else:
        return request


def run_model(model_image, request, output_dir=None):
    request = encode_referenced_files(request)
    request_string = quote(json.dumps(request))
    # output_otion = f"-o {output_dir}" if output_dir else ""
    output_option = "-o /outputs" if output_dir else ""
    cmd = f"node /usr/local/bin/runModel-cli.js -m {model_image} -i {request_string} -p 1 {output_option}"
    result = execute_shell(cmd)
    # parse json
    try:
        result = json.loads(result)
    except:  # noqa: E722
        pass
    # logging.info(f"got result", result)
    return result
