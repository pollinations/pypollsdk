import logging
import os
import shutil
import subprocess
import tempfile
import time

from postgrest.exceptions import APIError
from realtime.connection import Socket

from pypollsdk import constants
from pypollsdk.constants import supabase, supabase_api_key, supabase_id
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
        with BackgroundCommand(
            f"pollinate-cli.js --send --ipns --debounce 70 --path {tmpdir} > /tmp/cid"
        ):
            for key, value in request.items():
                if os.path.exists(value):
                    filename = value.split("/")[-1]
                    target = os.path.join(tmpdir, "input", filename)
                    shutil.copy(value, target)
                    value = filename

                path = f"{tmpdir}/input/{key}"
                with open(path, "w") as f:
                    f.write(value)
        with open("/tmp/cid") as f:
            cid = f.read().strip().split("\n")[-1].strip()

        return cid


class CloseSocket(Exception):
    pass


def wait_for_response(cid):
    url = f"wss://{supabase_id}.supabase.co/realtime/v1/websocket?apikey={supabase_api_key}&vsn=1.0.0"
    s = Socket(url)
    s.connect()
    channel = s.set_channel(f"realtime:public:{constants.db_name}")
    response = {}

    def unsubscribe_and_process(payload):
        if (
            payload["record"]["input"] == cid
            and payload["record"]["success"] is not None
        ):
            response.update(payload["record"])
            channel.off("UPDATE")
            raise CloseSocket

    channel.join().on("UPDATE", unsubscribe_and_process)
    try:
        s.listen()
    except CloseSocket:
        return response


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
            if response[0]["success"] is None:
                logging.info(f"Waiting for response for {cid}")
                response = wait_for_response(cid)
            return fetch_outputs_and_return(response[0], output_dir)
        except APIError as e:
            print(e)
        payload = {"input": cid, "image": self.image}
        data = supabase.table(constants.db_name).insert(payload).execute()
        assert len(data.data) > 0, f"Failed to insert {cid} into db"
        return fetch_outputs_and_return(wait_for_response(cid), output_dir)
