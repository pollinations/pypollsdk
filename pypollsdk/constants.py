
import requests
from dotenv import load_dotenv

load_dotenv()

db_name = "pollen"
test_image = "no-gpu-test-image"


model_index = (
    "https://raw.githubusercontent.com/pollinations/model-index/main/images.json"
)


def available_models():
    return list(requests.get(model_index).json().values()) + ["no-gpu-test-image"]
