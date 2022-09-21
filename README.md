# pypollsdk

SDK for the pollinations API.

## Install
```sh
# Install dependencies
pip install -e ".[test]"
```
Then, add your supabase API key to your `.env`.

## Usage
```python
from uuid import uuid4
model = Model("614871946825.dkr.ecr.us-east-1.amazonaws.com/pollinations/latent-diffusion-400m")
response = model.predict({"Prompt": f"a sign that says '{uuid4().hex[:5]}'"})
print(response)
>> {'input': 'QmT1iRxBYMPRYr72Z18P3YJDJw31vDhwJyvt9bCGwXKrVA',
    'image': '614871946825.dkr.ecr.us-east-1.amazonaws.com/pollinations/latent-diffusion-400m',
    'output': 'QmW2MZy6DYwBHV9e2yiCDrk1FvtmGzgonwYgCpj7vZqfk6',
    'pinned': False,
    'processing_started': True,
    'final_output': 'QmW2MZy6DYwBHV9e2yiCDrk1FvtmGzgonwYgCpj7vZqfk6',
    'logs': 'https://ipfs.pollinations.ai/ipfs/QmW2MZy6DYwBHV9e2yiCDrk1FvtmGzgonwYgCpj7vZqfk6/output/log',
    'request_submit_time': '2022-07-26T08:39:35.037518',
    'start_time': '2022-07-26T08:39:35',
    'end_time': '2022-07-26T08:40:50',
    'success': True}
```

## Test
```
pytest test
```
