import random
import pandas as pd
tasks = 37720 # p-tasks


mean_runtime_by_requester = {
    "arouf@ec41": 21658.80777,
    "arouf@ec34": 21312.9297,
    "arouf@ec35": 21014.34252,
    "arouf@ec36": 21000.07941,
    "arouf@ec44": 20982.82842,
    "arouf@ec42": 20899.44017,
    "arouf@ec48": 20834.38964,
    "arouf@ec33": 20806.08251,
    "arouf@ec43": 20360.90578,
    "arouf@ec45": 20295.78698,
    "arouf@ec46": 19414.51064,
    "arouf@ec4": 10528.23927,
    "arouf@ec5": 10421.31686,
    "arouf@ec22": 10405.88841,
    "arouf@ec10": 10348.47137,
    "arouf@ec21": 10345.22643,
    "arouf@ec16": 10334.2796,
    "arouf@ec9": 10309.95089,
    "arouf@ec8": 10289.56561,
    "arouf@ec17": 10262.95786,
    "arouf@ec19": 10257.71626,
    "arouf@ec6": 10202.23863,
    "arouf@ec23": 10167.02141,
    "arouf@ec12": 10117.73328,
    "arouf@ec7": 10059.17543,
    "arouf@ec38": 10037.82073,
    "arouf@ec20": 10017.07462,
    "arouf@ec2": 10012.33102,
    "arouf@ec24": 10006.64446,
    "arouf@ec15": 9971.429024,
    "arouf@ec18": 9888.778885,
    "arouf@ec29": 9754.052392,
    "arouf@ec40": 9500.306788,
    "arouf@ec39": 9481.839926,
    "arouf@ec37": 9474.434346,
    "arouf@ec30": 9448.903218,
    "arouf@ec31": 9403.659049,
    "arouf@ec32": 9249.969343,
    "x-arouf@a120.anvil.rcac.purdue.edu": 8653.942483,
    "x-arouf@a239.anvil.rcac.purdue.edu": 8589.832236,
    "x-arouf@a130.anvil.rcac.purdue.edu": 8442.410685,
    "x-arouf@a067.anvil.rcac.purdue.edu": 8338.892855,
    "x-arouf@a106.anvil.rcac.purdue.edu": 8170.32394,
    "x-arouf@a031.anvil.rcac.purdue.edu": 8014.924415,
    "x-arouf@a012.anvil.rcac.purdue.edu": 7924.037191,
    "x-arouf@a014.anvil.rcac.purdue.edu": 7911.672495,
    "x-arouf@a082.anvil.rcac.purdue.edu": 7897.280181,
    "x-arouf@a008.anvil.rcac.purdue.edu": 7896.501654,
    "x-arouf@a007.anvil.rcac.purdue.edu": 7889.783132,
    "x-arouf@a016.anvil.rcac.purdue.edu": 7884.4418,
    "x-arouf@a013.anvil.rcac.purdue.edu": 7883.767387,
    "x-arouf@a078.anvil.rcac.purdue.edu": 7882.06634,
    "x-arouf@a079.anvil.rcac.purdue.edu": 7876.65945,
    "x-arouf@a074.anvil.rcac.purdue.edu": 7853.519879,
    "x-arouf@a035.anvil.rcac.purdue.edu": 7819.869868,
    "x-arouf@a080.anvil.rcac.purdue.edu": 7803.903272,
    "x-arouf@a083.anvil.rcac.purdue.edu": 7799.544604,
    "x-arouf@a034.anvil.rcac.purdue.edu": 7763.758943,
    "x-arouf@a060.anvil.rcac.purdue.edu": 7736.501453,
    "x-arouf@a036.anvil.rcac.purdue.edu": 7718.087898,
    "arouf@ec143": 5204.619139,
    "arouf@ec166": 5138.969717,
    "arouf@ec168": 5137.815493,
    "arouf@ec138": 5133.67745,
    "arouf@ec136": 5130.610291,
    "arouf@ec187": 4122.299398,
    "arouf@ec191": 4108.40179,
    "arouf@ec192": 4103.086524
}

nodes = len(mean_runtime_by_requester) # q-nodes

average_task_times_on_node = [mean_runtime_by_requester[key] for key in mean_runtime_by_requester]

# Initial allocation of jobs on nodes
last_job_completion_time_on_node = average_task_times_on_node.copy()

# p-tasks allocated, therefore
tasks = tasks - nodes
count_of_tasks_on_node = [1] * nodes # each node initialized with their first job

while tasks != 0:
  # Find node that finished job and is available at the earliest
  node_available_for_next_job = last_job_completion_time_on_node.index(min(last_job_completion_time_on_node))

  # Task counter updated
  count_of_tasks_on_node[node_available_for_next_job] += 1
  
  # Increment time on node
  last_job_completion_time_on_node[node_available_for_next_job] += average_task_times_on_node[node_available_for_next_job]
  tasks -= 1


print(count_of_tasks_on_node)


print(average_task_times_on_node)

print(last_job_completion_time_on_node)

result_dict = {
    "machine_name": [key for key in mean_runtime_by_requester],
    "average_time_on_machine": [mean_runtime_by_requester[key] for key in mean_runtime_by_requester],
    "count": count_of_tasks_on_node,
    "last_timestamp": last_job_completion_time_on_node
}
df = pd.DataFrame(result_dict)

# Save to CSV
df.to_csv("dynamic_simulation.csv", index=False)