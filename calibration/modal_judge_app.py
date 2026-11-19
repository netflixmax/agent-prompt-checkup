import modal, json, re
image = (modal.Image.debian_slim(python_version="3.11")
         .pip_install("vllm==0.8.5", "transformers==4.51.3", "huggingface_hub[hf_transfer]")
         .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"}))
app = modal.App("judge-calibration", image=image)

@app.function(gpu="L40S", timeout=40*60)
def run_judge(model: str, prompts: list, system: str, max_tokens: int = 150, qwen3: bool = False):
    import time
    from vllm import LLM, SamplingParams
    t0 = time.time()
    llm = LLM(model=model, dtype="bfloat16", max_model_len=4096, gpu_memory_utilization=0.92)
    t_load = time.time() - t0
    tok = llm.get_tokenizer()
    texts = []
    for p in prompts:
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": p}]
        kw = {"enable_thinking": False} if qwen3 else {}
        texts.append(tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, **kw))
    sp = SamplingParams(temperature=0.0, max_tokens=max_tokens)
    t1 = time.time()
    outs = llm.generate(texts, sp)
    return {"model": model, "load_sec": round(t_load, 1), "gen_sec": round(time.time() - t1, 1),
            "outputs": [o.outputs[0].text for o in outs]}
