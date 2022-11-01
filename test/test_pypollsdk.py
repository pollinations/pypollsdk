from uuid import uuid4

from pypollsdk import run_model


def single_request_is_successful(prompt):
    """Return True if a single request is successful, otherwise fail"""
    response = run_model(
        "614871946825.dkr.ecr.us-east-1.amazonaws.com/pollinations/latent-diffusion-400m",
        {"prompt": prompt},
    )

    # check if response JSON has a key that ends ith .png
    assert any(key.endswith(".png") for key in response.keys())

    return True


def test_model():
    for _ in range(2):
        prompt = f"a sign that says '{uuid4().hex[:20]}'"
        assert single_request_is_successful(prompt)
        # Do it again to check if cached results are returned
        assert single_request_is_successful(prompt)


if __name__ == "__main__":
    test_model()
