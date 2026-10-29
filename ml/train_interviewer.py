"""QLoRA fine-tune of the interviewer on distilled interviews. Fits a 6 GB laptop GPU.

Usage (inside the ml container): python train_interviewer.py [epochs]
Output: models/interviewer-lora/ (adapter only, ~60 MB) + eval report printed at the end.
"""
import json
import random
import sys

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

BASE = 'Qwen/Qwen2.5-1.5B-Instruct'  # fits a 6 GB laptop GPU for QLoRA; 3B ran out of memory
OUT = 'models/interviewer-lora'
KEEP_TURNS = 6  # same window engine.py sends (messages[-7:]); keeps samples short enough for 6 GB VRAM


def load(path='data/interviewer.jsonl'):
    rows = [json.loads(l) for l in open(path, encoding='utf-8')]
    for r in rows:
        m = r['messages']
        r['messages'] = [m[0]] + m[1:][-(KEEP_TURNS + 1):]
    random.Random(0).shuffle(rows)
    cut = max(20, len(rows) // 10)
    return rows[cut:], rows[:cut]


def main(epochs=2):
    train, held = load()
    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForCausalLM.from_pretrained(
        BASE, device_map='auto', dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                                               bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
    trainer = SFTTrainer(
        model=model,
        processing_class=tok,
        train_dataset=Dataset.from_list([{'messages': r['messages']} for r in train]),
        eval_dataset=Dataset.from_list([{'messages': r['messages']} for r in held[:60]]),
        peft_config=LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, task_type='CAUSAL_LM',
                               target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj']),
        args=SFTConfig(
            output_dir='models/_ckpt', num_train_epochs=epochs, per_device_train_batch_size=1, per_device_eval_batch_size=1,
            gradient_accumulation_steps=8, torch_empty_cache_steps=1, learning_rate=2e-4, lr_scheduler_type='cosine', warmup_ratio=0.05,
            max_length=1024, assistant_only_loss=False, completion_only_loss=None, fp16=True,
            gradient_checkpointing=True, logging_steps=10, eval_strategy='epoch', save_strategy='no',
            report_to=[], optim='paged_adamw_8bit',
        ),
    )
    trainer.train()
    trainer.model.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    json.dump({'base': BASE, 'train_samples': len(train), 'held_out': len(held),
               'eval_loss': trainer.evaluate().get('eval_loss')}, open(OUT + '/train_info.json', 'w'), indent=2)
    print(open(OUT + '/train_info.json').read())


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
