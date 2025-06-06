import pandas as pd
import matplotlib.pyplot as plt
import os

path = 'tests/benchmarks/benchmark_results.csv'
if not os.path.exists(path):
    raise FileNotFoundError(f"No CSV at {os.path.abspath(path)}")

# Load data
df = pd.read_csv(path)

# Clean data
df_clean = df.groupby(['name','filename']).agg({
    'mean (ms)': 'mean',
    'ops/sec': 'mean'
}).reset_index()

# Sort by performance
df_sorted = df_clean.sort_values('mean (ms)')

# Plotting
plt.figure(figsize=(10,6))
plt.barh(df_sorted['name'], df_sorted['mean (ms)'])
plt.title('Search Algorithm Performance (1M Lines)')
plt.xlabel('Mean Time (ms)')
plt.tight_layout()
plt.savefig('performance.png')