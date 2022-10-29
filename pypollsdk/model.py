import json
import logging
import os
import subprocess
from shlex import quote

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG)


def execute_shell(cmd):
    print(cmd)
    return subprocess.check_output(cmd, shell=True).decode("utf-8").split("\n")[0]

def run_model(model_image, request, output_dir=None):
    request_string = quote(json.dumps(request))
    # output_otion = f"-o {output_dir}" if output_dir else ""
    output_option = f"-o /outputs" if output_dir else ""
    cmd = f"node /usr/local/bin/runModel-cli.js -m {model_image} -i {request_string} -p 1 {output_option}"
    result = execute_shell(cmd)
    # parse json
    try:
        result = json.loads(result)
    except:
        pass
    logging.info(f"got result", result)
    return result
