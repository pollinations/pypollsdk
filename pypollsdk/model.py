import json
import logging
import os
import shutil
import tempfile

from postgrest.exceptions import APIError

from pypollsdk import constants
from pypollsdk.constants import supabase

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)


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
    print(
        f"pollinate-cli.js --nodeid {cid} --debounce 70 --path {output_dir} --subfolder /output --receive"
    )
    os.system(
        f"pollinate-cli.js --nodeid {cid} --debounce 70 --path {output_dir} --subfolder /output --receive"
    )


class Model:
    """Wrapper for requests to the pollinations API"""

    def __init__(self, image, allowed_paths=["/tmp", "/outputs", "."]):
        self.image = image
        self.allowed_paths = [os.path.abspath(i) for i in allowed_paths]

    def predict(self, request, output_dir):
        """Run a single prediction on the model"""
        data = self.predict_async(request)
        cid = data["input"]
        logging.info(f"Waiting for response for {cid}")
        wait_and_sync(cid, output_dir)
        return

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
            "priority": 1,
        }
        response = supabase.table(constants.db_name).insert(payload).execute().data
        assert len(response) > 0, f"Failed to insert {cid} into db"
        return response[0]
