"""Wrapper to run a cogmodel locally and keep the container alive for multiple requests

Usage:
```
from pypollsdk import RunningCogModel

request = {
    "images_zip": "https://pollinations-ci-bucket.s3.amazonaws.com/img.zip"
}

with RunningCogModel("clip-enc", "data") as model:
    response = model.predict(request, "data")
    print(response)
```


"""

import base64
import datetime as dt
import json
import logging
import os
import shutil
import time
from mimetypes import guess_extension

import docker
import requests

docker_client = docker.from_env()


class UnhealthyCogContainer(Exception):
    pass


loaded_model = None
MAX_NUM_POLLEN_UNTIL_RESTART = 100


class RunningCogModel:
    def __init__(
        self,
        image,
        output_path,
        has_gpu=True,
        environment=dict(
            SUPABASE_URL=os.environ.get("SUPABASE_URL"),
            SUPABASE_API_KEY=os.environ.get("SUPABASE_API_KEY"),
            SUPABASE_ID=os.environ.get("SUPABASE_ID"),
            OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY"),
        ),
    ):
        self.image_name = image
        self.image = docker_client.images.get(image)
        self.output_path = os.path.abspath(output_path)
        self.container = None
        self.pollen_start_time = None
        self.pollen_since_container_start = 0
        self.has_gpu = has_gpu
        self.environment = environment

    def __enter__(self):
        print(self.output_path)
        global loaded_model
        # Check if the container is already running
        self.pollen_start_time = dt.datetime.now()
        try:
            running_image = docker_client.containers.get("cogmodel").image
        except docker.errors.NotFound:
            running_image = None
        if (
            self.image == running_image
            and self.pollen_since_container_start < MAX_NUM_POLLEN_UNTIL_RESTART
        ):
            self.pollen_since_container_start += 1
            logging.info(f"Model already loaded: {self.image}")
            return self
        # Kill the running container if it is not the same model
        self.kill_cog_model(logs=False)
        os.makedirs(self.output_path, exist_ok=True)
        self.pollen_since_container_start = 0
        # Start the container
        if self.has_gpu:
            gpus = [
                docker.types.DeviceRequest(
                    count=1,
                    capabilities=[["gpu"]],
                )
            ]
        else:
            gpus = []
        container = docker_client.containers.run(
            self.image,
            detach=True,
            name="cogmodel",
            ports={"5000/tcp": 5000},
            volumes={self.output_path: {"bind": "/outputs", "mode": "rw"}},
            remove=True,
            auto_remove=True,
            device_requests=gpus,
            stderr=True,
            tty=True,
            environment=self.environment,
        )
        logging.info(f"Starting {self.image}: {container}")
        # Wait for the container to start
        self.wait_until_cogmodel_is_healthy()
        loaded_model = self.image_name
        return self

    def __exit__(self, type, value, traceback):
        # write container logs to output folder
        self.write_logs()

    def write_logs(self):
        try:
            logs = (
                docker_client.containers.get("cogmodel")
                .logs(stdout=True, stderr=True, since=self.pollen_start_time)
                .decode("utf-8")
            )
            write_folder(self.output_path, "log", logs)
        except (docker.errors.NotFound, docker.errors.APIError):
            pass

    def shutdown(self):
        self.write_logs()
        self.kill_cog_model()

    def kill_cog_model(self, logs=True):
        # get cogmodel logs and write them to output folder and kill container
        for _ in range(5):
            try:
                container = docker_client.containers.get("cogmodel")
                if logs:
                    self.write_logs()
                container.kill()
                logging.info(f"Killed {self.image}")
                time.sleep(1)
                container.remove()
            except docker.errors.NotFound:
                return
            except docker.errors.APIError:
                time.sleep(1)

    def wait_until_cogmodel_is_healthy(self, timeout=40 * 60):
        # Wait for the container to start
        logging.info(f"Waiting for {self.image} to start")
        for i in range(timeout):
            try:
                assert (
                    requests.get(
                        "http://localhost:5000/",
                    ).status_code
                    == 200
                )
                logging.info(f"Model healthy: {self.image}")
                return
            except:  # noqa
                time.sleep(1)
        raise UnhealthyCogContainer(f"Model unhealthy: {self.image}")

    def _clear_output_folder(self):
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)
            return
        for file in os.listdir(self.output_path):
            file_path = os.path.join(self.output_path, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(e)

    def predict(self, inputs):
        logging.info("Send to cog model")
        # clean output folder including dirs
        self._clear_output_folder()
        # Send message to cog container
        payload = {"input": inputs}
        response = requests.post("http://localhost:5000/predictions", json=payload)
        logging.info(f"response: {response}")
        write_folder(self.output_path, "time_start", str(int(time.time())))
        write_folder(self.output_path, "done", "true")
        if response.status_code != 200:
            write_folder(self.output_path, "cog_response", json.dumps(response.text))
            write_folder(self.output_path, "success", "false")
        else:
            self.write_http_response_files(response)
            write_folder(self.output_path, "done", "true")
            logging.info(f"Set done to true in {self.output_path}")
        return response

    def write_http_response_files(self, response):
        try:
            output = response.json()["output"]
            if not isinstance(output, list):
                output = [output]
            for i, encoded_file in enumerate(output):
                try:
                    encoded_file = encoded_file["file"]
                except TypeError:
                    pass  # already a string
                meta, encoded = encoded_file.split(";base64,")
                extension = guess_extension(meta.split(":")[1])
                with open(f"{self.output_path}/out_{i}{extension}", "wb") as f:
                    f.write(base64.b64decode(encoded))
        except Exception as e:  # noqa
            pass


def write_folder(path, key, value, mode="w"):
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/{key}", mode) as f:
        f.write(value)
