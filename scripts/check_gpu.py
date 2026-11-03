"""GPU smoke test: load a small Qwen model and time a short generation.

Run inside WSL2 with the training deps installed:
    uv run --group train python scripts/check_gpu.py [--model Qwen/Qwen3-0.6B]
Prints the device, VRAM used and tokens per second, so we know the 6 GB card
can host the policy before any training code is written.
"""

from __future__ import annotations

import argparse
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description="Load a small Qwen model on the GPU and generate.")
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--tokens", type=int, default=64)
    args = parser.parse_args()

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        print("Training deps missing. Run: uv sync --group train", file=sys.stderr)
        return 1

    if not torch.cuda.is_available():
        print("CUDA not available to PyTorch. Check the NVIDIA driver and WSL2 setup.")
        return 1

    props = torch.cuda.get_device_properties(0)
    print(f"device: {props.name}, {props.total_memory / 2**30:.1f} GB, torch {torch.__version__}")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16, device_map="cuda")
    messages = [{"role": "user", "content": "In one sentence, what does SQLite WAL mode do?"}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

    torch.cuda.synchronize()
    start = time.perf_counter()
    output = model.generate(**inputs, max_new_tokens=args.tokens, do_sample=False)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    new_tokens = output.shape[1] - inputs["input_ids"].shape[1]
    text = tokenizer.decode(output[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    print(f"model: {args.model}")
    print(f"vram peak: {torch.cuda.max_memory_allocated() / 2**30:.2f} GB")
    print(f"speed: {new_tokens / elapsed:.1f} tokens/s ({new_tokens} tokens in {elapsed:.1f} s)")
    print(f"reply: {text.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
