import pandas as pd

# Load the dataset
df = pd.read_csv("raw_dataset.csv")

# Group by requested_by and calculate:
# - the first request_timestamp
# - the last completion_timestamp
summary = df.groupby("requested_by").agg(
    first_request_timestamp=("request_timestamp", "min"),
    last_completion_timestamp=("completion_timestamp", "max")
).reset_index()

# Add a new column: engagement_duration = last - first
summary["engagement_duration"] = summary["last_completion_timestamp"] - summary["first_request_timestamp"]

# Save the result to CSV
summary.to_csv("request_summary.csv", index=False)
