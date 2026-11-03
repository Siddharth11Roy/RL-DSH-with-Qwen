# Setting up WSL2 for training

Training needs vLLM, which only runs on Linux. On Windows we use WSL2 with Ubuntu.
The GPU is shared with WSL through the normal Windows NVIDIA driver, so nothing
CUDA-related is installed inside Ubuntu itself.

## 1. Check the GPU is visible

```bash
wsl -d Ubuntu-22.04 -- nvidia-smi
```

You should see the RTX 3050 6 GB. If not, update the Windows NVIDIA driver.

## 2. Install uv and Node inside Ubuntu

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
nvm install 24
```

Node 24 is needed: the practice world uses `node:sqlite`, and DeepSeek Harness asks for Node 24.9 or newer.

## 3. Clone the repo inside the Linux filesystem

Working from `/mnt/d/...` is slow for many small files, so keep a WSL copy:

```bash
mkdir -p ~/code && cd ~/code
git clone https://Siddharth11Roy@github.com/Siddharth11Roy/RL-DSH-with-Qwen.git
cd RL-DSH-with-Qwen
git config user.name "Siddharth Roy"
git config user.email "siddharth1126@gmail.com"
```

## 4. Install and run the GPU smoke test

```bash
uv sync --group train
uv run --group train python scripts/check_gpu.py
```

This downloads PyTorch (a few GB) and Qwen3-0.6B, then prints VRAM use and tokens per second.
Run `uv run rlh doctor` afterwards to confirm the rest of the setup.
