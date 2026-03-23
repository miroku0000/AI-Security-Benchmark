# Models in temperature study
temp_models = [
    "claude-opus-4-6", "claude-sonnet-4-5", "codegemma", "codellama",
    "deepseek-coder", "deepseek-coder_6.7b-instruct", "gemini-2.5-flash",
    "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-5.2",
    "gpt-5.4", "gpt-5.4-mini", "llama3.1", "mistral",
    "qwen2.5-coder", "qwen2.5-coder_14b", "starcoder2"
]

# All baseline models
baseline_models = [
    "gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini",
    "gpt-5.2", "gpt-5.4", "gpt-5.4-mini",
    "o1", "o3", "o3-mini",
    "claude-opus-4-6", "claude-sonnet-4-5",
    "gemini-2.5-flash",
    "codellama", "deepseek-coder", "deepseek-coder:6.7b-instruct",
    "starcoder2", "codegemma", "mistral", "llama3.1",
    "qwen2.5-coder", "qwen2.5-coder:14b",
    "cursor", "codex-app"
]

# Normalize names
temp_normalized = [m.replace(':', '_') for m in temp_models]
baseline_normalized = [m.replace(':', '_') for m in baseline_models]

print("Models in temperature study: 19")
print("Models in baseline: 24")
print("\nMissing from temperature study (need baseline run):")
missing = [m for m in baseline_normalized if m not in temp_normalized]
for m in missing:
    print(f"  - {m}")

print(f"\nTotal missing: {len(missing)}")
print("\n✅ Already have from temperature study (can use temp 0.5 or any temp):")
present = [m for m in baseline_normalized if m in temp_normalized]
for m in present:
    print(f"  - {m}")
print(f"\nTotal already done: {len(present)}")
