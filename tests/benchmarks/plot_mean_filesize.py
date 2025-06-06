import os

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

path = 'tests/benchmarks/benchmark_results.csv'
if not os.path.exists(path):
    raise FileNotFoundError(f"No CSV at {os.path.abspath(path)}")

# Load data
df = pd.read_csv(path)


# Clean and preprocess the data
# Convert filename to numeric line count
#  Custom filename-to-lines converter
def filename_to_lines(filename):
    num_part = filename.replace('.txt', '')
    if 'k' in num_part:
        return int(float(num_part.replace('k', '')) * 1000)
    elif 'm' in num_part:
        return int(float(num_part.replace('m', '')) * 1000000)
    return int(num_part)


df['lines'] = df['filename'].apply(filename_to_lines)
df['mean_s'] = df['mean (ms)'] / 1000
# Create a pivot table for easier plotting
pivot_df = df.pivot_table(
    index='lines',
    columns='name',
    values='mean_s',
    aggfunc='mean'
)

# Sort the index for proper line plotting
pivot_df = pivot_df.sort_index()

# Create the plot
plt.figure(figsize=(12, 7))
ax = plt.gca()

# Custom color cycle for better differentiation
colors = plt.cm.viridis.colors[::64][:len(pivot_df.columns)]
markers = ['o', 's', 'D', '^', 'v', 'p', '*']

# Plot each algorithm
for i, (col, color, marker) in enumerate(zip(pivot_df.columns, colors, markers)):
    pivot_df[col].plot(
        ax=ax,
        logx=True,
        logy=True,
        marker=marker,
        markersize=8,
        linewidth=2,
        color=color,
        linestyle='--' if col == 'grep' else '-',
        label=col.capitalize()
    )

# Formatting
ax.set_title('Search Algorithm Performance Comparison', fontsize=14, pad=20)
ax.set_xlabel('Number of Lines in File (log scale)', fontsize=12)
ax.set_ylabel('Mean Execution Time (seconds, log scale)', fontsize=12)
ax.grid(True, which='both', linestyle='--', alpha=0.7)
ax.legend(title='Algorithm', title_fontsize=12, fontsize=10)

# Custom x-axis ticks
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'{int(x/1000)}' if x >= 1000 else int(x)))
ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=5))

# Custom y-axis formatting
ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))
ax.yaxis.set_minor_formatter(ticker.NullFormatter())

# Add data labels for grep to highlight poor performance
grep_data = pivot_df['grep']
for x, y in zip(grep_data.index, grep_data.values):
    if x >= 100000:  # Only label large files for readability
        ax.text(x, y, f'{y:.3f}s',
                ha='left', va='bottom',
                fontsize=8, color=colors[list(pivot_df.columns).index('grep')])

plt.tight_layout()
plt.savefig('performance_comparison.png', dpi=300, bbox_inches='tight')
plt.show()
