import pandas as pd

tasks = 37720 # p-tasks

first_request_timestamp = {
    "arouf@ec10": 1746223214,
    "arouf@ec12": 1746210759,
    "arouf@ec136": 1746232833,
    "arouf@ec138": 1746233266,
    "arouf@ec143": 1746232878,
    "arouf@ec15": 1746210778,
    "arouf@ec16": 1746211331,
    "arouf@ec166": 1746232549,
    "arouf@ec168": 1746233368,
    "arouf@ec17": 1746210808,
    "arouf@ec18": 1746210830,
    "arouf@ec187": 1746232418,
    "arouf@ec19": 1746210804,
    "arouf@ec191": 1746233551,
    "arouf@ec192": 1746232533,
    "arouf@ec2": 1746210756,
    "arouf@ec20": 1746210816,
    "arouf@ec21": 1746210843,
    "arouf@ec22": 1746210796,
    "arouf@ec23": 1746210799,
    "arouf@ec24": 1746210863,
    "arouf@ec29": 1746210788,
    "arouf@ec30": 1746210772,
    "arouf@ec31": 1746210858,
    "arouf@ec32": 1746210853,
    "arouf@ec33": 1746210815,
    "arouf@ec34": 1746210915,
    "arouf@ec35": 1746210875,
    "arouf@ec36": 1746210907,
    "arouf@ec37": 1746283959,
    "arouf@ec38": 1746210878,
    "arouf@ec39": 1746210834,
    "arouf@ec4": 1746223216,
    "arouf@ec40": 1746210865,
    "arouf@ec41": 1746210879,
    "arouf@ec42": 1746210900,
    "arouf@ec43": 1746210927,
    "arouf@ec44": 1746210935,
    "arouf@ec45": 1746210777,
    "arouf@ec46": 1746210860,
    "arouf@ec48": 1746210920,
    "arouf@ec5": 1746210956,
    "arouf@ec6": 1746210942,
    "arouf@ec7": 1746210753,
    "arouf@ec8": 1746210945,
    "arouf@ec9": 1746210755,
    "x-arouf@a007.anvil.rcac.purdue.edu": 1746553374,
    "x-arouf@a008.anvil.rcac.purdue.edu": 1746552052,
    "x-arouf@a012.anvil.rcac.purdue.edu": 1746553447,
    "x-arouf@a013.anvil.rcac.purdue.edu": 1746553415,
    "x-arouf@a014.anvil.rcac.purdue.edu": 1746552251,
    "x-arouf@a016.anvil.rcac.purdue.edu": 1746552218,
    "x-arouf@a031.anvil.rcac.purdue.edu": 1746552152,
    "x-arouf@a034.anvil.rcac.purdue.edu": 1746552088,
    "x-arouf@a035.anvil.rcac.purdue.edu": 1746552187,
    "x-arouf@a036.anvil.rcac.purdue.edu": 1746552120,
    "x-arouf@a060.anvil.rcac.purdue.edu": 1746219005,
    "x-arouf@a067.anvil.rcac.purdue.edu": 1746811496,
    "x-arouf@a074.anvil.rcac.purdue.edu": 1746219101,
    "x-arouf@a078.anvil.rcac.purdue.edu": 1746219128,
    "x-arouf@a079.anvil.rcac.purdue.edu": 1746219207,
    "x-arouf@a080.anvil.rcac.purdue.edu": 1746219156,
    "x-arouf@a082.anvil.rcac.purdue.edu": 1746219181,
    "x-arouf@a083.anvil.rcac.purdue.edu": 1746219233,
    "x-arouf@a106.anvil.rcac.purdue.edu": 1746811389,
    "x-arouf@a120.anvil.rcac.purdue.edu": 1746812640,
    "x-arouf@a130.anvil.rcac.purdue.edu": 1746812676,
    "x-arouf@a239.anvil.rcac.purdue.edu": 1746811316
}
mean_runtime_by_requester = {
    "arouf@ec10": 10348.47137,
    "arouf@ec12": 10117.73328,
    "arouf@ec136": 5130.610291,
    "arouf@ec138": 5133.67745,
    "arouf@ec143": 5204.619139,
    "arouf@ec15": 9971.429024,
    "arouf@ec16": 10334.2796,
    "arouf@ec166": 5138.969717,
    "arouf@ec168": 5137.815493,
    "arouf@ec17": 10262.95786,
    "arouf@ec18": 9888.778885,
    "arouf@ec187": 4122.299398,
    "arouf@ec19": 10257.71626,
    "arouf@ec191": 4108.40179,
    "arouf@ec192": 4103.086524,
    "arouf@ec2": 10012.33102,
    "arouf@ec20": 10017.07462,
    "arouf@ec21": 10345.22643,
    "arouf@ec22": 10405.88841,
    "arouf@ec23": 10167.02141,
    "arouf@ec24": 10006.64446,
    "arouf@ec29": 9754.052392,
    "arouf@ec30": 9448.903218,
    "arouf@ec31": 9403.659049,
    "arouf@ec32": 9249.969343,
    "arouf@ec33": 20806.08251,
    "arouf@ec34": 21312.9297,
    "arouf@ec35": 21014.34252,
    "arouf@ec36": 21000.07941,
    "arouf@ec37": 9474.434346,
    "arouf@ec38": 10037.82073,
    "arouf@ec39": 9481.839926,
    "arouf@ec4": 10528.23927,
    "arouf@ec40": 9500.306788,
    "arouf@ec41": 21658.80777,
    "arouf@ec42": 20899.44017,
    "arouf@ec43": 20360.90578,
    "arouf@ec44": 20982.82842,
    "arouf@ec45": 20295.78698,
    "arouf@ec46": 19414.51064,
    "arouf@ec48": 20834.38964,
    "arouf@ec5": 10421.31686,
    "arouf@ec6": 10202.23863,
    "arouf@ec7": 10059.17543,
    "arouf@ec8": 10289.56561,
    "arouf@ec9": 10309.95089,
    "x-arouf@a007.anvil.rcac.purdue.edu": 7889.783132,
    "x-arouf@a008.anvil.rcac.purdue.edu": 7896.501654,
    "x-arouf@a012.anvil.rcac.purdue.edu": 7924.037191,
    "x-arouf@a013.anvil.rcac.purdue.edu": 7883.767387,
    "x-arouf@a014.anvil.rcac.purdue.edu": 7911.672495,
    "x-arouf@a016.anvil.rcac.purdue.edu": 7884.4418,
    "x-arouf@a031.anvil.rcac.purdue.edu": 8014.924415,
    "x-arouf@a034.anvil.rcac.purdue.edu": 7763.758943,
    "x-arouf@a035.anvil.rcac.purdue.edu": 7819.869868,
    "x-arouf@a036.anvil.rcac.purdue.edu": 7718.087898,
    "x-arouf@a060.anvil.rcac.purdue.edu": 7736.501453,
    "x-arouf@a067.anvil.rcac.purdue.edu": 8338.892855,
    "x-arouf@a074.anvil.rcac.purdue.edu": 7853.519879,
    "x-arouf@a078.anvil.rcac.purdue.edu": 7882.06634,
    "x-arouf@a079.anvil.rcac.purdue.edu": 7876.65945,
    "x-arouf@a080.anvil.rcac.purdue.edu": 7803.903272,
    "x-arouf@a082.anvil.rcac.purdue.edu": 7897.280181,
    "x-arouf@a083.anvil.rcac.purdue.edu": 7799.544604,
    "x-arouf@a106.anvil.rcac.purdue.edu": 8170.32394,
    "x-arouf@a120.anvil.rcac.purdue.edu": 8653.942483,
    "x-arouf@a130.anvil.rcac.purdue.edu": 8442.410685,
    "x-arouf@a239.anvil.rcac.purdue.edu": 8589.832236
}
last_completion_timestamp = {
    "arouf@ec10": 1746664071,
    "arouf@ec12": 1746641828,
    "arouf@ec136": 1746478120,
    "arouf@ec138": 1746478129,
    "arouf@ec143": 1746477976,
    "arouf@ec15": 1746713595,
    "arouf@ec16": 1746641129,
    "arouf@ec166": 1746478233,
    "arouf@ec168": 1746477732,
    "arouf@ec17": 1746641800,
    "arouf@ec18": 1746642389,
    "arouf@ec187": 1746900832,
    "arouf@ec19": 1746640528,
    "arouf@ec191": 1746898033,
    "arouf@ec192": 1746900356,
    "arouf@ec2": 1746636135,
    "arouf@ec20": 1746639484,
    "arouf@ec21": 1746642700,
    "arouf@ec22": 1746665481,
    "arouf@ec23": 1746641951,
    "arouf@ec24": 1746639205,
    "arouf@ec29": 1746642195,
    "arouf@ec30": 1746642302,
    "arouf@ec31": 1746640692,
    "arouf@ec32": 1746641517,
    "arouf@ec33": 1746664515,
    "arouf@ec34": 1746640610,
    "arouf@ec35": 1746664815,
    "arouf@ec36": 1746665186,
    "arouf@ec37": 1746633673,
    "arouf@ec38": 1746640596,
    "arouf@ec39": 1746641468,
    "arouf@ec4": 1746664415,
    "arouf@ec40": 1746653285,
    "arouf@ec41": 1746654551,
    "arouf@ec42": 1746642292,
    "arouf@ec43": 1746665137,
    "arouf@ec44": 1746664645,
    "arouf@ec45": 1746641264,
    "arouf@ec46": 1746641074,
    "arouf@ec48": 1746640913,
    "arouf@ec5": 1746641964,
    "arouf@ec6": 1746639943,
    "arouf@ec7": 1746640010,
    "arouf@ec8": 1746642468,
    "arouf@ec9": 1746642708,
    "x-arouf@a007.anvil.rcac.purdue.edu": 1746812367,
    "x-arouf@a008.anvil.rcac.purdue.edu": 1746900774,
    "x-arouf@a012.anvil.rcac.purdue.edu": 1746642214,
    "x-arouf@a013.anvil.rcac.purdue.edu": 1746899566,
    "x-arouf@a014.anvil.rcac.purdue.edu": 1746641313,
    "x-arouf@a016.anvil.rcac.purdue.edu": 1746812619,
    "x-arouf@a031.anvil.rcac.purdue.edu": 1746641786,
    "x-arouf@a034.anvil.rcac.purdue.edu": 1746477988,
    "x-arouf@a035.anvil.rcac.purdue.edu": 1746900471,
    "x-arouf@a036.anvil.rcac.purdue.edu": 1746478282,
    "x-arouf@a060.anvil.rcac.purdue.edu": 1746898550,
    "x-arouf@a067.anvil.rcac.purdue.edu": 1746642455,
    "x-arouf@a074.anvil.rcac.purdue.edu": 1746811125,
    "x-arouf@a078.anvil.rcac.purdue.edu": 1746900315,
    "x-arouf@a079.anvil.rcac.purdue.edu": 1746898307,
    "x-arouf@a080.anvil.rcac.purdue.edu": 1746811012,
    "x-arouf@a082.anvil.rcac.purdue.edu": 1746900450,
    "x-arouf@a083.anvil.rcac.purdue.edu": 1746810811,
    "x-arouf@a106.anvil.rcac.purdue.edu": 1746641588,
    "x-arouf@a120.anvil.rcac.purdue.edu": 1746641796,
    "x-arouf@a130.anvil.rcac.purdue.edu": 1746642053,
    "x-arouf@a239.anvil.rcac.purdue.edu": 1746641308
}


df_engagement = pd.read_csv("request_summary.csv")
df_machine_stat = pd.read_csv("machine_completion_times.csv")

for key in first_request_timestamp:
    first_request_timestamp[key] = df_engagement[df_engagement["requested_by"] == key]["first_request_timestamp"].values[0]
    last_completion_timestamp[key] = df_engagement[df_engagement["requested_by"] == key]["last_completion_timestamp"].values[0]
    mean_runtime_by_requester[key] = df_machine_stat[df_machine_stat["requested_by"] == key]["mean"].values[0]


print(mean_runtime_by_requester)

# Use actual data
node_names = list(mean_runtime_by_requester.keys())
nodes = len(node_names)
print(node_names)
# Mean runtime per node (seconds)
average_task_times_on_node = [mean_runtime_by_requester[n] for n in node_names]

# Node availability (start times)
initial_time_when_node_became_available = [first_request_timestamp[n] for n in node_names]

# Track last job end time per node
last_job_completion_time_on_node = initial_time_when_node_became_available.copy()

# Initialize task count
count_of_tasks_on_node = [0] * nodes

# Simultaneous node count
simultanous_nodes = [(8 if "ec" in node_names[i] else 32) for i in range(len(node_names))]
# Greedy task assignment loop
print(simultanous_nodes)

while tasks > 0:
    # Pick node that becomes available the earliest
    node = last_job_completion_time_on_node.index(min(last_job_completion_time_on_node))

    # Assign task
    count_of_tasks_on_node[node] += simultanous_nodes[node]

    # Advance node availability time
    last_job_completion_time_on_node[node] += average_task_times_on_node[node]

    # Decrement remaining tasks
    tasks -= simultanous_nodes[node]
    # print("Node ", node_names[node], simultanous_nodes[node], last_job_completion_time_on_node[node])

# Final stats
print("Assigned Tasks per Node:")
for i, name in enumerate(node_names):
    print(f"{name:50s} | Tasks: {count_of_tasks_on_node[i]} | Final Time: {last_job_completion_time_on_node[i]:.2f}")

result_dict = {
    "machine_name": node_names, 
    "start_timestamp": [first_request_timestamp[node_name] for node_name in node_names],
    "actual_end_timestamp": [last_completion_timestamp[node_name] for node_name in node_names],
    "speculated_end_timestamp": last_job_completion_time_on_node
}  


df = pd.DataFrame(result_dict)

# Save to CSV
df.to_csv("speculative_time.csv", index=False)  
    