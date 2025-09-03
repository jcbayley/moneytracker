#!/usr/bin/env python3
import torch
import platform
import sys
import os
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    TrainerCallback
)
from peft import (
    LoraConfig, 
    get_peft_model, 
    TaskType
)
from datasets import Dataset
import json
import argparse
from typing import Dict, List

class ProgressCallback(TrainerCallback):
    """Custom callback to show training progress clearly."""
    
    def __init__(self, total_steps):
        self.total_steps = total_steps
        self.start_time = None
    
    def on_train_begin(self, args, state, control, **kwargs):
        import time
        self.start_time = time.time()
        print(f"🚀 Training started - {self.total_steps} total steps")
    
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs is not None and 'loss' in logs:
            import time
            elapsed = time.time() - self.start_time if self.start_time else 0
            progress = (state.global_step / self.total_steps) * 100
            
            print(f"Step {state.global_step:4d}/{self.total_steps} ({progress:5.1f}%) | "
                  f"Loss: {logs['loss']:.4f} | "
                  f"LR: {logs.get('learning_rate', 0):.2e} | "
                  f"Elapsed: {elapsed/60:.1f}m")
    
    def on_train_end(self, args, state, control, **kwargs):
        import time
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"✅ Training completed in {elapsed/60:.1f} minutes")

# Check available hardware and libraries
def check_environment():
    """Check what hardware and libraries are available"""
    env_info = {
        'platform': platform.system(),
        'machine': platform.machine(),
        'cuda_available': torch.cuda.is_available(),
        'mps_available': torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False,
        'quantization_available': False,
        'bitsandbytes_available': False
    }
    
    # Check for quantization libraries
    try:
        from transformers import BitsAndBytesConfig
        from peft import prepare_model_for_kbit_training
        import bitsandbytes
        env_info['quantization_available'] = True
        env_info['bitsandbytes_available'] = True
    except ImportError:
        pass
    
    return env_info

def setup_device_and_dtype(env_info):
    """Setup optimal device and data type based on available hardware"""
    if env_info['cuda_available']:
        device = "cuda"
        torch_dtype = torch.float16
        print("🚀 Using CUDA GPU with float16")
    elif env_info['mps_available']:
        device = "mps" 
        torch_dtype = torch.float16
        print("🍎 Using Apple MPS (Metal) with float16")
    else:
        device = "cpu"
        torch_dtype = torch.float32  # CPU needs float32
        print("🔧 Using CPU with float32 (will be slower)")
    
    return device, torch_dtype

def setup_model_and_tokenizer(model_name: str, lora_rank: int = 32, lora_alpha: int = 64, 
                               lora_dropout: float = 0.1, use_quantization: bool = False, 
                               continue_from: str = None):
    """
    Setup model with LoRA adapters, with quantization if available
    Args:
        continue_from: Path to existing LoRA checkpoint to continue training from
    """
    env_info = check_environment()
    device, torch_dtype = setup_device_and_dtype(env_info)
    
    model_kwargs = {
        'trust_remote_code': True,
        'torch_dtype': torch_dtype,
    }
    
    # Setup quantization if available and requested
    if use_quantization and env_info['quantization_available'] and env_info['cuda_available']:
        print("🔥 Using 4-bit quantization")
        from transformers import BitsAndBytesConfig
        from peft import prepare_model_for_kbit_training
        
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model_kwargs['quantization_config'] = bnb_config
        model_kwargs['device_map'] = "auto"
        
    elif device != "cpu":
        # Use device_map for GPU/MPS without quantization
        model_kwargs['device_map'] = "auto"
    else:
        # For CPU, we'll move manually
        pass
    
    # Load model
    print(f"Loading model: {model_name}")
    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
    
    # Move to device if CPU
    if device == "cpu":
        model = model.to(device)
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Add padding token if missing
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    
    # Prepare model for training
    if use_quantization and env_info['quantization_available'] and env_info['cuda_available']:
        model = prepare_model_for_kbit_training(model)
    else:
        # Enable gradient checkpointing for memory efficiency
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
    
    # LoRA configuration
    if "phi" in model_name.lower():
        target_modules = ["q_proj", "k_proj", "v_proj", "dense"]
    elif "qwen" in model_name.lower():
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    elif "smollm" in model_name.lower():
        # SmolLM uses Llama-style architecture
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    else:
        # Mistral/Llama style models
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    
    lora_config = LoraConfig(
        r=lora_rank,
        lora_alpha=lora_alpha,
        target_modules=target_modules,
        lora_dropout=lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    # Add LoRA adapters or load existing ones
    if continue_from and os.path.exists(continue_from):
        print(f"🔄 Loading existing LoRA adapters from {continue_from}")
        from peft import PeftModel
        try:
            # Load existing PEFT model
            model = PeftModel.from_pretrained(model, continue_from)
            print("✅ Successfully loaded existing LoRA adapters")
        except Exception as e:
            print(f"⚠️  Failed to load existing LoRA adapters: {e}")
            print("🔄 Creating new LoRA adapters instead")
            model = get_peft_model(model, lora_config)
    else:
        if continue_from:
            print(f"⚠️  Continue-from path not found: {continue_from}")
            print("🔄 Creating new LoRA adapters instead")
        model = get_peft_model(model, lora_config)
    
    model.print_trainable_parameters()
    
    return model, tokenizer, device, torch_dtype

def load_and_tokenize_data(data_path: str, tokenizer, max_length: int = 512):
    """Load and tokenize training data"""
    texts = []
    with open(data_path, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            texts.append(data['text'])
    
    print(f"Loaded {len(texts)} text examples")
    print(f"Sample text length: {len(texts[0]) if texts else 0} characters")
    
    def tokenize_function(examples):
        # Tokenize the text
        result = tokenizer(
            examples['text'],
            truncation=True,
            padding=False,  # We'll pad dynamically in data collator
            max_length=max_length,
            return_tensors=None
        )
        
        # For causal language modeling, labels are the same as input_ids
        result["labels"] = result["input_ids"].copy()
        return result
    
    dataset = Dataset.from_dict({'text': texts})
    tokenized_dataset = dataset.map(
        tokenize_function, 
        batched=True,
        remove_columns=dataset.column_names,  # Remove original text column
        desc="Tokenizing data"
    )
    
    print(f"Tokenized dataset size: {len(tokenized_dataset)}")
    if len(tokenized_dataset) > 0:
        print(f"Sample tokenized length: {len(tokenized_dataset[0]['input_ids'])}")
    
    return tokenized_dataset

def main():
    parser = argparse.ArgumentParser(description='Cross-Platform LoRA Fine-tuning')
    parser.add_argument('--model', type=str, default='HuggingFaceTB/SmolLM-360M',
                       help='Model name (default: HuggingFaceTB/SmolLM-360M)')
    parser.add_argument('--data', type=str, required=True,
                       help='Path to training data (JSONL format)')
    parser.add_argument('--output', type=str, default='./lora-output',
                       help='Output directory for trained model')
    parser.add_argument('--rank', type=int, default=32,
                       help='LoRA rank (lower = less memory, higher = more trainable parameters)')
    parser.add_argument('--lora-alpha', type=int, default=64,
                       help='LoRA alpha parameter (scaling factor)')
    parser.add_argument('--lora-dropout', type=float, default=0.1,
                       help='LoRA dropout rate')
    parser.add_argument('--epochs', type=int, default=3,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Per-device batch size')
    parser.add_argument('--lr', type=float, default=2e-4,
                       help='Learning rate')
    parser.add_argument('--max-length', type=int, default=512,
                       help='Maximum sequence length')
    parser.add_argument('--quantize', action='store_true',
                       help='Use 4-bit quantization (if available)')
    parser.add_argument('--cpu-only', action='store_true',
                       help='Force CPU-only training')
    parser.add_argument('--continue-from', type=str, default=None,
                       help='Path to existing LoRA checkpoint to continue training from (e.g., ./lora-output)')
    parser.add_argument('--logging-steps', type=int, default=10,
                       help='Logging frequency in steps')
    
    args = parser.parse_args()
    
    # Override device if requested
    if args.cpu_only:
        torch.backends.mps.is_available = lambda: False
        torch.cuda.is_available = lambda: False
        print("🔧 Forcing CPU-only mode")
    
    print(f"Setting up LoRA fine-tuning for {args.model}")
    print(f"LoRA rank: {args.rank} (alpha: {args.lora_alpha}, dropout: {args.lora_dropout})")
    print(f"Training data: {args.data}")
    if args.continue_from:
        print(f"Continuing from checkpoint: {args.continue_from}")
    
    # Check environment
    env_info = check_environment()
    print(f"Environment: {env_info}")
    
    # Setup model and tokenizer
    try:
        model, tokenizer, device, torch_dtype = setup_model_and_tokenizer(
            args.model, args.rank, args.lora_alpha, args.lora_dropout, 
            args.quantize and not args.cpu_only, args.continue_from
        )
    except Exception as e:
        print(f"❌ Model setup failed: {e}")
        print("💡 Try with smaller model or --cpu-only flag")
        sys.exit(1)
    
    # Load and tokenize data
    print("Loading training data...")
    try:
        train_dataset = load_and_tokenize_data(args.data, tokenizer, args.max_length)
        print(f"Loaded {len(train_dataset)} training examples")
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        sys.exit(1)
    
    # Data collator for causal language modeling
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # We're doing causal LM, not masked LM
        pad_to_multiple_of=8,
        return_tensors="pt"
    )
    
    # Adjust training arguments based on device
    gradient_accumulation_steps = 8 if device == "cpu" else 4
    dataloader_num_workers = 0 if device == "cpu" else 2
    
    training_args = TrainingArguments(
        output_dir=args.output,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        logging_steps=args.logging_steps,
        save_steps=args.logging_steps * 10,  # Save checkpoints every 10x logging frequency
        save_strategy="steps",
        eval_strategy="no",
        warmup_steps=100,
        lr_scheduler_type="cosine",
        remove_unused_columns=False,
        report_to="none",
        dataloader_num_workers=dataloader_num_workers,
        dataloader_pin_memory=False,
        logging_first_step=True,  # Log the first step
        logging_nan_inf_filter=False,  # Show NaN/Inf in logs
        
        # Device-specific optimizations  
        fp16=(torch_dtype == torch.float16 and device == "cuda"),  # Only use fp16 on CUDA
        bf16=False,  # Most hardware doesn't support bf16
        gradient_checkpointing=True,
        
        # Optimizer selection
        optim="adamw_torch",
    )
    
    print(f"Training arguments: batch_size={args.batch_size}, "
          f"grad_accum={gradient_accumulation_steps}, "
          f"effective_batch_size={args.batch_size * gradient_accumulation_steps}, "
          f"logging_steps={args.logging_steps}")
    
    total_steps = len(train_dataset) * args.epochs // (args.batch_size * gradient_accumulation_steps)
    print(f"Total training steps: {total_steps}")
    print(f"Loss will be logged every {args.logging_steps} steps")
    print(f"Checkpoints saved every {args.logging_steps * 10} steps")
    
    # Initialize trainer with progress callback
    progress_callback = ProgressCallback(total_steps)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=[progress_callback],
    )
    
    # Clear cache before training
    if device == "cuda":
        torch.cuda.empty_cache()
    elif device == "mps":
        torch.mps.empty_cache()
    
    try:
        trainer.train()
        
        # Save the final model
        print(f"💾 Saving final model to {args.output}")
        trainer.save_model()
        tokenizer.save_pretrained(args.output)
        
        # Show final training metrics
        if trainer.state.log_history:
            final_loss = trainer.state.log_history[-1].get('train_loss', 'N/A')
            print(f"📊 Final training loss: {final_loss}")
        
        print("🎉 Training complete!")
        print(f"📁 Model saved to: {args.output}")
        print(f"🔧 To continue training: --continue-from {args.output}")
        print(f"💡 To test: Use the saved model in your AI query settings")
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        print("💡 Try reducing --batch-size, --rank, or --max-length")
        sys.exit(1)

if __name__ == "__main__":
    main()
