import logging
import os
import shutil
import subprocess
import tempfile
import time

from postgrest.exceptions import APIError

from pypollsdk import constants
from pypollsdk.constants import supabase
from pypollsdk.ipfs_download import download_output

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)


class BackgroundCommand:
    def __init__(self, cmd):
        self.cmd = cmd

    def __enter__(self):
        self.proc = subprocess.Popen(
            f"exec {self.cmd}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.proc

    def __exit__(self, type, value, traceback):
        time.sleep(15)
        logging.info(f"Killing background command: {self.cmd}")
        self.proc.kill()
        try:
            logs, errors = self.proc.communicate(timeout=2)
            logging.info(f"   Logs: {logs.decode('utf-8')}")
            logging.error(f"   errors: {errors.decode('utf-8')}")
        except subprocess.TimeoutExpired:
            pass


def upload_request_to_ipfs(request):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "input"))
        for key, value in request.items():
            if os.path.exists(value):
                filename = value.split("/")[-1]
                target = os.path.join(tmpdir, "input", filename)
                shutil.copy(value, target)
                value = filename

            path = f"{tmpdir}/input/{key}"
            with open(path, "w") as f:
                f.write(value)

        os.system(
            f"pollinate-cli.js --once --send --ipns --debounce 70 --path {tmpdir} > /tmp/cid"
        )
        with open("/tmp/cid") as f:
            cid = f.read().strip().split("\n")[-1].strip()

        return cid


class CloseSocket(Exception):
    pass


def wait_for_response(cid):
    # poll until success is not null
    while True:
        try:
            pollen = (
                supabase.table(constants.db_name)
                .select("*")
                .eq("input", cid)
                .single()
                .execute()
                .data
            )
            if pollen["success"] is not None:
                return pollen
        except APIError:
            pass
        time.sleep(1)


def fetch_outputs_and_return(pollen, output_dir):
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        download_output(pollen["output"], output_dir)
    return pollen


class Model:
    """Wrapper for requests to the pollinations API"""

    def __init__(self, image):
        self.image = image

    def predict(self, request, output_dir=None):
        """Run a single prediction on the model"""
        return predict(self.image, request, output_dir)

    def predict_async(self, request):
        return predict_async(self.image, request)



def predict(model_image, request, output_dir=None):
    """Run a single prediction on the model"""
    data = predict_async(model_image, request)
    cid = data["input"]
    if data["success"] is None:
        logging.info(f"Waiting for response for {cid}")
        data = wait_for_response(cid)
    return fetch_outputs_and_return(data, output_dir)


def predict_async(model_image, request):
    request["model_image"] = model_image
    cid = upload_request_to_ipfs(request)
    try:
        response = (
            supabase.table(constants.db_name)
            .select("*")
            .eq("input", cid)
            .execute()
            .data
        )
        assert len(response) == 1
        return response[0]
    except (APIError, AssertionError) as e:
        print(e)
    payload = {"input": cid, "image": model_image, "priority": 5}
    response = supabase.table(constants.db_name).insert(payload).execute().data
    assert len(response) > 0, f"Failed to insert {cid} into db"
    return response[0]
