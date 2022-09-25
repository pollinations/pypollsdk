#!/usr/bin/env python
# coding: utf-8
import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, Union

import requests


def ipfs_dir_to_json(cid: str):
    """Get a CID of a dir in IPFS and return a dict. Runs "node /usr/local/bin/getcid-cli.js [cid]
    with {filename: filecontent} structure, where
        - files with file extension are skipped
        - filecontents containing a filename are resolved to absolute URIs
    """
    logging.info(f"Fetching IPFS dir {cid}")

    # use subprocess to run getcid-cli.js

    proc = subprocess.Popen(
        ["node", "/usr/local/bin/getcid-cli.js", cid],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        logging.error(f"Error while fetching IPFS dir {cid}: {stderr}")
        sys.exit(1)

    # parse stdout to json
    json_str = stdout.decode("utf-8")
    print(json_str)
    json_dict = json.loads(json_str)

    return json_dict


def ipfs_subfolder_to_json(cid: str, subdir: str) -> Dict[str, Any]:
    """Get the contents of a subdir of a cid as json"""
    json_dict = ipfs_dir_to_json(cid)
    return json_dict[subdir]


def is_downloadable(url: str) -> bool:
    """Check if a url is downloadable"""
    if url.startswith("http"):
        return True
    return False


def try_download_file(url: str, target: str):
    """Download a file to a local directory"""
    logging.info(f"Downloading {url} to {target}")
    if url.startswith("http"):
        try:
            # create target directory
            os.makedirs(os.path.dirname(target), exist_ok=True)
            r = requests.get(url, allow_redirects=True)
            with open(target, "wb") as f:
                f.write(r.content)
        except Exception as e:
            logging.error(f"Error while downloading {url}: {e}")


def download_files_recursive(
    maybe_files: Union[dict, list, str], target: str, downloaded: list = None
):
    if downloaded is None:
        downloaded = []
    if maybe_files in downloaded:
        return downloaded
    if isinstance(maybe_files, str):
        try_download_file(maybe_files, target)
        return downloaded + [maybe_files]
    elif isinstance(maybe_files, list):
        for i, item in maybe_files:
            downloaded += download_files_recursive(
                item, os.path.join(target, str(i)), downloaded
            )
        return downloaded
    elif isinstance(maybe_files, dict):
        for key, value in maybe_files.items():
            downloaded += download_files_recursive(
                value, os.path.join(target, key), downloaded
            )
        return downloaded
    else:
        return downloaded


def download_output(cid: str, output_dir: str, downloaded: list = None):
    """Download the output of a pollinate run to a local directory"""
    output = ipfs_dir_to_json(cid)["output"]
    if output is None:
        return output, []
    downloaded = download_files_recursive(output, output_dir, downloaded)
    return output, downloaded
