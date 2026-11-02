with open("src/evaluation/benchmark_builder.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find and delete lines corresponding to R18 and R19 in initial_llm_errors
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if '"R18": {' in line and i < 650:
        start_idx = i
    if start_idx is not None and '"R19": {' in line:
        pass
    if start_idx is not None and line.strip() == '}' and i > start_idx + 15:
        end_idx = i
        break

print(f"Removing lines {start_idx} to {end_idx}")
assert start_idx is not None and end_idx is not None
del lines[start_idx:end_idx]

with open("src/evaluation/benchmark_builder.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Updated src/evaluation/benchmark_builder.py successfully")
