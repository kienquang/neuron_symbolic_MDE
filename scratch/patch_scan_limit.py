with open('src/evaluation/benchmark_builder.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'df_propagated["case:concept:name"].drop_duplicates().iloc[:2500].tolist()'
replacement = 'df_propagated["case:concept:name"].drop_duplicates().iloc[:600].tolist()'

assert target in text, 'target not found'
text = text.replace(target, replacement)

with open('src/evaluation/benchmark_builder.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Successfully optimized trace scan limit in benchmark_builder.py!')
