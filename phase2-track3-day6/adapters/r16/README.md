---
base_model: unsloth/Llama-3.2-3B-Instruct-bnb-4bit
library_name: peft
tags:
- lora
- qlora
- finance
- llama-3.2
- unsloth
---

# Llama-3.2-3B Finance Alpaca LoRA Adapter

This repository contains a LoRA/QLoRA adapter fine-tuned for finance-style instruction following on a 200-sample subset of `gbharti/finance-alpaca`.

## Training Summary

- Base model: `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`
- Dataset: `gbharti/finance-alpaca`
- Samples used: 200 total, 180 train, 20 eval
- LoRA rank: r=16, alpha=32
- Target modules: q/k/v/o + gate/up/down projections
- GPU: Tesla T4 16 GB
- Eval loss: 2.0142
- Eval perplexity: 7.49

## Usage

```python
from unsloth import FastLanguageModel
from peft import PeftModel

base_model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Llama-3.2-3B-Instruct-bnb-4bit",
    max_seq_length=512,
    dtype=None,
    load_in_4bit=True,
)
model = PeftModel.from_pretrained(base_model, "daosonn/lab21-llama32-3b-finance-alpaca-lora-r16")
```
