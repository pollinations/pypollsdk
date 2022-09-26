import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from shlex import quote

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)


def upload_request_to_ipfs(request):

    # stringify request
    request_string = quote(json.dumps(request))
    image = request["model_image"]
    cmd = f"node /usr/local/bin/runModel-cli.js {image} {request_string} true"
    cid = execute_shell(cmd)
    logging.info(f"submitted {cid}")
    return cid

def wait_and_sync(cid, output_dir=None):
    # poll until success is not null
    print(
        f"pollinate-cli.js --nodeid {cid} --debounce 70 --path {output_dir} --subfolder /output --receive"
    )
    os.system(
        f"pollinate-cli.js --nodeid {cid} --debounce 70 --path {output_dir} --subfolder /output --receive"
    )

class Model:
    """Wrapper for requests to the pollinations API"""

    def __init__(self, image):
        self.image = image

    def predict(self, request, output_dir):
        """Run a single prediction on the model"""
        cid = self.predict_async(request)
        logging.info(f"Waiting for response for {cid}")
        wait_and_sync(cid, output_dir)
        return

    def predict_async(self, request):
        request["model_image"] = self.image
        cid = upload_request_to_ipfs(request)
        logging.info(f"Request sent with cid: {cid}")
        return cid

def execute_shell(cmd):
    return subprocess.check_output(cmd, shell=True).decode("utf-8").split("\n")[0]
