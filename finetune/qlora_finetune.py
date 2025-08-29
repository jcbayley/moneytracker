#!/usr/bin/env python3
import torch
import platform
import sys
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
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

def setup_model_and_tokenizer(model_name: str, lora_rank: int = 16, use_quantization: bool = False):
    """
    Setup model with LoRA adapters, with quantization if available
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
        lora_alpha=32,
        target_modules=target_modules,
        lora_dropout=0.1,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    
    # Add LoRA adapters
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
    parser.add_argument('--rank', type=int, default=16,
                       help='LoRA rank (lower = less memory)')
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
    
    args = parser.parse_args()
    
    # Override device if requested
    if args.cpu_only:
        torch.backends.mps.is_available = lambda: False
        torch.cuda.is_available = lambda: False
        print("🔧 Forcing CPU-only mode")
    
    print(f"Setting up LoRA fine-tuning for {args.model}")
    print(f"LoRA rank: {args.rank}")
    print(f"Training data: {args.data}")
    
    # Check environment
    env_info = check_environment()
    print(f"Environment: {env_info}")
    
    # Setup model and tokenizer
    try:
        model, tokenizer, device, torch_dtype = setup_model_and_tokenizer(
            args.model, args.rank, args.quantize and not args.cpu_only
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
        logging_steps=10,
        save_steps=500,
        save_strategy="steps",
        eval_strategy="no",
        warmup_steps=100,
        lr_scheduler_type="cosine",
        remove_unused_columns=False,
        report_to="none",
        dataloader_num_workers=dataloader_num_workers,
        dataloader_pin_memory=False,
        
        # Device-specific optimizations  
        fp16=(torch_dtype == torch.float16 and device == "cuda"),  # Only use fp16 on CUDA
        bf16=False,  # Most hardware doesn't support bf16
        gradient_checkpointing=True,
        
        # Optimizer selection
        optim="adamw_torch",
    )
    
    print(f"Training arguments: batch_size={args.batch_size}, "
          f"grad_accum={gradient_accumulation_steps}, "
          f"effective_batch_size={args.batch_size * gradient_accumulation_steps}")
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
    )
    
    # Clear cache before training
    if device == "cuda":
        torch.cuda.empty_cache()
    elif device == "mps":
        torch.mps.empty_cache()
    
    print("🚀 Starting training...")
    print(f"Expected time: {len(train_dataset) * args.epochs // (args.batch_size * gradient_accumulation_steps)} steps")
    
    try:
        trainer.train()
        print("✅ Training completed successfully!")
    except Exception as e:
        print(f"❌ Training failed: {e}")
        print("💡 Try reducing --batch-size, --rank, or --max-length")
        sys.exit(1)
    
    # Save the final model
    print(f"Saving model to {args.output}")
    trainer.save_model()
    tokenizer.save_pretrained(args.output)
    
    print("🎉 Training complete!")
    print(f"📁 Model saved to: {args.output}")
    print(f"🔧 To use: Load LoRA adapters from {args.output}")

if __name__ == "__main__":
    main()
