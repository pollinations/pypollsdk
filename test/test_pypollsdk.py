from uuid import uuid4

import requests

from pypollsdk import Model


def test_model():
    model = Model(
        "614871946825.dkr.ecr.us-east-1.amazonaws.com/pollinations/latent-diffusion-400m"
    )
    prompt = f"a sign that says '{uuid4().hex[:5]}'"
    response = model.predict({"Prompt": prompt})
    assert response["success"] is True
    assert response["output"] is not None
    response = requests.get(
        f"https://ipfs.pollinations.ai/ipfs/{response['output']}/input/Prompt"
    )
    assert prompt == response.json()
