models = [
    "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini",
    "gpt-5.2", "gpt-5.4", "gpt-5.4-mini",
    "claude-opus-4-6", "claude-sonnet-4-5",
    "gemini-2.5-flash",
    "codellama", "deepseek-coder", "deepseek-coder:6.7b-instruct",
    "starcoder2", "codegemma", "mistral", "llama3.1",
    "qwen2.5-coder", "qwen2.5-coder:14b"
]
temps = ["0.0", "0.5", "0.7", "1.0"]

with open("temperature_study_20260321_193151.log") as f:
    log = f.read()

missing = []
for model in models:
    for temp in temps:
        if f"generated code for {model} at temperature {temp}" not in log:
            missing.append(f"{model} temp {temp}")

print(f"Missing {len(missing)} runs:")
for m in missing:
    print(f"  - {m}")
