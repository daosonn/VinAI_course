import argparse
from pathlib import Path

import torch
from peft import PeftModel
from unsloth import FastLanguageModel


DEFAULT_BASE_MODEL = "unsloth/Llama-3.2-3B-Instruct-bnb-4bit"
DEFAULT_ADAPTER_DIR = Path(__file__).resolve().parent / "adapters" / "r16"

ALPACA_TEMPLATE_NO_INPUT = """### Instruction:
{instruction}

### Response:
"""


def load_base(model_name: str, max_seq_length: int):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    FastLanguageModel.for_inference(model)
    return model, tokenizer


def generate(model, tokenizer, question: str, max_new_tokens: int, temperature: float, top_p: float) -> str:
    prompt = ALPACA_TEMPLATE_NO_INPUT.format(instruction=question)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(output[0], skip_special_tokens=True)
    return text.split("### Response:")[-1].strip()


def main():
    parser = argparse.ArgumentParser(
        description="Compare base Llama-3.2-3B response vs base + local LoRA adapter response."
    )
    parser.add_argument("question", nargs="?", help="Question to ask the model.")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter-dir", default=str(DEFAULT_ADAPTER_DIR))
    parser.add_argument("--max-seq-length", type=int, default=512)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.9)
    args = parser.parse_args()

    question = args.question or input("Question: ").strip()
    if not question:
        raise SystemExit("Question is empty.")

    adapter_dir = Path(args.adapter_dir)
    if not (adapter_dir / "adapter_model.safetensors").exists():
        raise FileNotFoundError(f"Missing adapter_model.safetensors in {adapter_dir}")
    if not (adapter_dir / "adapter_config.json").exists():
        raise FileNotFoundError(f"Missing adapter_config.json in {adapter_dir}")

    print("Loading base model...")
    base_model, tokenizer = load_base(args.base_model, args.max_seq_length)
    base_answer = generate(
        base_model,
        tokenizer,
        question,
        args.max_new_tokens,
        args.temperature,
        args.top_p,
    )

    print("Loading LoRA adapter on top of the same base model...")
    finetuned_model = PeftModel.from_pretrained(base_model, str(adapter_dir))
    finetuned_model.eval()
    finetuned_answer = generate(
        finetuned_model,
        tokenizer,
        question,
        args.max_new_tokens,
        args.temperature,
        args.top_p,
    )

    print("\n" + "=" * 88)
    print("QUESTION")
    print("=" * 88)
    print(question)

    print("\n" + "=" * 88)
    print("1) BASE MODEL")
    print("=" * 88)
    print(base_answer)

    print("\n" + "=" * 88)
    print("2) BASE MODEL + FINETUNED LoRA r=16")
    print("=" * 88)
    print(finetuned_answer)


if __name__ == "__main__":
    main()
