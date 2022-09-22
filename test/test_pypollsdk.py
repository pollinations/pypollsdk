from uuid import uuid4

import requests

from pypollsdk import Model


def single_request_is_successful(prompt):
    """Return True if a single request is successful, otherwise fail"""
    model = Model(
        "614871946825.dkr.ecr.us-east-1.amazonaws.com/pollinations/latent-diffusion-400m"
    )
    response = model.predict({"prompt": prompt})
    assert response["success"] is True
    assert response["output"] is not None
    out_cid = response["output"].strip()
    output_prompt = requests.get(
        f"https://ipfs.pollinations.ai/ipfs/{out_cid}/input/prompt"
    )
    assert prompt == eval(output_prompt.text)
    return True


def test_model():
    for _ in range(2):
        prompt = f"a sign that says '{uuid4().hex[:20]}'"
        assert single_request_is_successful(prompt)
        # Do it again to check if cached results are returned
        assert single_request_is_successful(prompt)


if __name__ == "__main__":
    test_model()
