import os

import requests
import wget


def first_true(iterable, default=None, pred=None):
    return next(filter(pred, iterable), default)


def named_list_to_dict(object_list):
    return {i["Name"]: i for i in object_list}


def download_output(cid, target):
    object_list = requests.get(
        f"https://ipfs.pollinations.ai/api/v0/ls?arg={cid}"
    ).json()["Objects"][0]["Links"]
    metadata = named_list_to_dict(object_list)
    return download_dir(metadata["output"]["Hash"], target)


def download_dir(cid, target):
    os.makedirs(target, exist_ok=True)
    object_list = requests.get(
        f"https://ipfs.pollinations.ai/api/v0/ls?arg={cid}"
    ).json()["Objects"][0]["Links"]
    metadata = named_list_to_dict(object_list)
    for name, value in metadata.items():
        url = f"https://ipfs.pollinations.ai/ipfs/{value['Hash']}"
        filename = f"{target}/{name}"
        try:
            wget.download(url, filename)
        except ValueError:
            r = requests.get(url, allow_redirects=True)
            with open(filename, "wb") as f:
                f.write(r.content)
