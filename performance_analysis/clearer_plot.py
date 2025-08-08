import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# Set style for better visual clarity with bigger text
plt.style.use('default')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['xtick.labelsize'] = 7
plt.rcParams['ytick.labelsize'] = 11
plt.rcParams['legend.fontsize'] = 12

# Load data
df = pd.read_csv("dynamic_simulation.csv")

# Convert average time to hours
df["average_time_hours"] = df["average_time_on_machine"] / 3600

# Normalize only average_time_hours
scaler = MinMaxScaler()
df["avg_time_normalized"] = scaler.fit_transform(df[["average_time_hours"]])

# Scale by max count
max_count = df["count"].max()
df["scaled_avg_time"] = df["avg_time_normalized"] * max_count

# Extract and simplify hostname
def simplify_hostname(full_name):
    host = full_name.split("@")[1]
    if "anvil.rcac.purdue.edu" in host:
        return host.split(".")[0]  # Just 'a067'
    return host

df["hostname"] = df["machine_name"].apply(simplify_hostname)

# Create the plot with dual y-axes
fig, ax1 = plt.subplots(figsize=(14, 6))

# Create second y-axis
ax2 = ax1.twinx()

# Use better colors and styling
bar_width = 0.4
index = range(len(df))

# Create bars in the same order as original
ax2.bar([i + bar_width/2 for i in index], df["scaled_avg_time"], 
        width=bar_width, label='Average Task Runtime (Normalized w.r.t Task Count)', 
        color='orange', alpha=0.8, edgecolor='darkorange', linewidth=1)

ax1.bar([i - bar_width/2 for i in index], df["count"], 
        width=bar_width, label='Task Count', 
        color='skyblue', alpha=0.8, edgecolor='steelblue', linewidth=1)

# Set labels for both y-axes (not bold)
ax1.set_xlabel("Machine Hostname", fontsize=11)
ax1.set_ylabel("Task Count", fontsize=11, color='skyblue')
ax2.set_ylabel("Average Task Runtime (Normalized)", fontsize=11, color='orange')

# Improve x-axis formatting
ax1.set_xticks(index)
ax1.set_xticklabels(df["hostname"], rotation=45, ha='right', fontsize=9)

# Add grid for better readability
ax1.grid(True, axis='y', alpha=0.3, linestyle='--', linewidth=1)

# Set y-axis colors to match the bars
ax1.tick_params(axis='y', labelcolor='skyblue', labelsize=9)
ax2.tick_params(axis='y', labelcolor='orange', labelsize=9)

# Set right y-axis to show actual data range with normalized tick labels
max_scaled = df["scaled_avg_time"].max()
ax2.set_yticks([0, max_scaled*0.2, max_scaled*0.4, max_scaled*0.6, max_scaled*0.8, max_scaled])
ax2.set_yticklabels(['0', '0.2', '0.4', '0.6', '0.8', '1.0'])

# Add legend in the middle to avoid overlapping
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, 1.0))

# Adjust layout for better spacing
plt.tight_layout()

plt.savefig("task_vs_scaled_time_clear.pdf", dpi=300, bbox_inches='tight')
plt.show() 