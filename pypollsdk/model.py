import json
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
        except subprocess.TimeoutExpired:
            pass


def upload_request_to_ipfs(request, allowed_paths=[]):
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "input"))
        for key, value in request.items():
            str_value = str(value)
            if os.path.exists(str_value):
                # check if the referenced paths is in one of the paths from which we allow uploads
                if any(
                    [
                        os.path.commonpath([os.path.abspath(str_value), allowed_path])
                        == allowed_path
                        for allowed_path in allowed_paths
                    ]
                ):
                    filename = str_value.split("/")[-1]
                    target = os.path.join(tmpdir, "input", filename)
                    shutil.copy(str_value, target)
                    value = filename

            path = f"{tmpdir}/input/{key}"
            with open(path, "w") as f:
                f.write(json.dumps(value))

        os.system(
            f"pollinate-cli.js --once --send --ipns --debounce 70 --path {tmpdir} > /tmp/cid"
        )
        with open("/tmp/cid") as f:
            cid = f.read().strip().split("\n")[-1].strip()

        return cid


class CloseSocket(Exception):
    pass


def wait_and_sync(cid, output_dir=None):
    # poll until success is not null
    downloaded = []
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
    previous_output_cid = None
    output = {}
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
            if (
                output_dir is not None
                and pollen["output"] is not None
                and pollen["output"] != previous_output_cid
            ):
                previous_output_cid = pollen["output"]
                try:
                    output, downloaded = download_output(
                        pollen["output"], output_dir, downloaded=downloaded
                    )
                except Exception as e:
                    logging.error(f"{e}")
            if pollen["success"] is not None:
                return pollen, output
        except APIError:
            pass
        time.sleep(1)


class Model:
    """Wrapper for requests to the pollinations API"""

    def __init__(self, image, allowed_paths=["/tmp", "/outputs", "."]):
        self.image = image
        self.allowed_paths = [os.path.abspath(i) for i in allowed_paths]

    def predict(self, request, output_dir=None):
        """Run a single prediction on the model"""
        data = self.predict_async(request)
        cid = data["input"]
        logging.info(f"Waiting for response for {cid}")
        pollen, output = wait_and_sync(cid, output_dir)
        pollen["output_json"] = output
        if output_dir is not None:
            with open(os.path.join(output_dir, "output.json"), "w") as f:
                f.write(json.dumps(pollen))
        return pollen

    def predict_async(self, request):
        request["model_image"] = self.image
        cid = upload_request_to_ipfs(request, self.allowed_paths)
        print(f"Request sent with cid: {cid}")
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
        payload = {
            "input": cid,
            "image": self.image,
            "priority": request.get("priority", 0),
        }
        response = supabase.table(constants.db_name).insert(payload).execute().data
        assert len(response) > 0, f"Failed to insert {cid} into db"
        return response[0]
