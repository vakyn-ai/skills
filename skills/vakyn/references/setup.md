# Setup: model file, server, API key

Goal: a running open-server, an API key in an environment variable, and `GET /v1/models` answering.
Check what is already there before installing anything: `command -v vakyn`, `vakyn status`,
`curl -s http://127.0.0.1:8080/api/status`.

## Choose a model file

Models are on Hugging Face as folders: `vakyn/VAKYN-0.8B-UQFF`, `vakyn/VAKYN-2B-UQFF`,
`vakyn/VAKYN-4B-UQFF`. Each folder holds three quantizations; the server uses `Q8_0` unless told
otherwise with `--quant Q6K` or `--quant Q4K`.

| Model | Q8_0 | Q6K | Q4K |
|---|---|---|---|
| 0.8B | 0.80 GB | 0.68 GB | 0.49 GB |
| 2B | 2.00 GB | 1.67 GB | 1.19 GB |
| 4B | 4.47 GB | 3.60 GB | 2.53 GB |

GPU memory the server needs with default settings (full 65,536-token context):
0.8B 7.9 GB, 2B 9.0 GB, 4B 19.7 GB. With `--ctx-size 8192`: 3.0, 4.2 and 8.7 GB.

How to pick:

1. Ask for the hardware, or read it: `nvidia-smi --query-gpu=name,memory.free,compute_cap --format=csv`,
   `uname -m`, `sysctl -n machdep.cpu.brand_string` (macOS), free RAM.
2. **Default: 4B Q8_0.** It gives the best answers. Use it when the GPU has the memory for it.
3. Not enough GPU memory: first lower `--ctx-size` to what their documents need (most tickets and
   messages are under 2,000 tokens). Then step down the size: 2B, then 0.8B.
4. Pick `Q6K` or `Q4K` only when memory is tight; they drift further from full precision. If the
   larger model fits only as `Q4K`, prefer it over a smaller model at `Q8_0`.
5. CPU only or Apple Silicon: it works, with the same answers, more slowly. Start with 2B or 0.8B and
   measure on their own documents (`vakyn-check`).

## Install the server

```sh
# Linux and macOS (Apple Silicon)
curl -fsSL https://github.com/vakyn-ai/open-server/releases/latest/download/install.sh | sh
# Windows (PowerShell)
irm https://github.com/vakyn-ai/open-server/releases/latest/download/install.ps1 | iex
```

The installer picks the right build (CPU, CUDA per GPU family, Metal) and puts `vakyn` in
`~/.local/bin`. Linux builds need glibc 2.35 or newer; on other Linux systems use Docker.
Show the person the command and let them run it; it changes their system.

## Download a model and start

```sh
hf download vakyn/VAKYN-4B-UQFF --local-dir ./VAKYN-4B-UQFF
vakyn serve --model ./VAKYN-4B-UQFF                 # Q8_0
vakyn serve --model ./VAKYN-4B-UQFF --quant Q4K     # smaller file
vakyn start --model ./VAKYN-4B-UQFF                 # same, in the background
```

`hf` comes with `pip install -U huggingface_hub`. The model loads in the background; until it is
ready the API answers `503` with `retry-after`. On first start the server prints a generated admin
password for the dashboard at `http://127.0.0.1:8080/`.

Useful flags: `--host`/`--port` (default `127.0.0.1:8080`), `--ctx-size`, `--max-queue` (default 32,
then `429`), `--cpu`, `--data-dir`. Linux service: `vakyn service install --model /path/VAKYN-4B-UQFF`.

### Docker

```sh
docker run -d --name vakyn -p 8080:8080 -v vakyn-data:/data \
  -v "$PWD/VAKYN-4B-UQFF:/models/VAKYN-4B-UQFF:ro" \
  ghcr.io/vakyn-ai/open-server:latest-cpu serve --model /models/VAKYN-4B-UQFF
```

GPU: image `latest-cuda` and `--gpus all` (needs the NVIDIA Container Toolkit).
`docker logs vakyn` shows the admin password; `docker exec vakyn vakyn keys create --name app` makes a key.

## Get an API key

`vakyn keys create --name my-app`, or the dashboard's API keys page. The key starts with `vk_` and
is shown once. Ask the person to put it in their environment themselves, for example a git-ignored
`.env` file:

```sh
VAKYN_BASE_URL=http://127.0.0.1:8080
VAKYN_API_KEY=vk_...
# for the official SDKs:
TYPESAFE_BASE_URL=http://127.0.0.1:8080
TYPESAFE_API_KEY=vk_...
```

Check `.env` is in `.gitignore` before they save it. Never ask them to paste the key into the chat.

Do not open or print `.env`: no `cat`, no `grep`, no file viewer. Load it inside the command that
needs it, so the key never shows in the chat:

```sh
set -a; . ./.env; set +a; curl -s "$VAKYN_BASE_URL/v1/models" -H "Authorization: Bearer $VAKYN_API_KEY"
```

To check the key is there without showing it: `set -a; . ./.env; set +a; [ -n "$VAKYN_API_KEY" ] && echo set`.

## Check

```sh
curl -s "$VAKYN_BASE_URL/v1/models" -H "Authorization: Bearer $VAKYN_API_KEY"
```

Expect the loaded model and the `jev-latest` alias. Then make the [first call](../SKILL.md#first-call).

| Symptom | Cause |
|---|---|
| connection refused | server not running, or a different host/port |
| `401` | key missing, mistyped or revoked |
| `503` with `retry-after` | model still loading |
| startup fails with a GPU memory message | lower `--ctx-size`, pick a smaller model, or `--quant Q4K`; the message names what fits |
