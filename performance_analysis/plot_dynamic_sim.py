import matplotlib.pyplot as plt
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

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

# Plot
fig, ax = plt.subplots(figsize=(14, 6))
bar_width = 0.4
index = range(len(df))

ax.bar([i - bar_width/2 for i in index], df["count"], width=bar_width, label='Task Count', color='skyblue')
ax.bar([i + bar_width/2 for i in index], df["scaled_avg_time"], width=bar_width, label='Scaled Avg Time (hrs)', color='orange')

ax.set_title("Task Count vs Scaled Avg Runtime per Machine")
ax.set_xlabel("Machine Hostname")
ax.set_ylabel("Count / Scaled Runtime")
ax.set_xticks(index)
ax.set_xticklabels(df["hostname"], rotation=90)
ax.legend()

plt.tight_layout()
plt.savefig("task_vs_scaled_time.png", dpi=300)  # Save as PNG
# plt.show()  # Optional: Uncomment to also display
