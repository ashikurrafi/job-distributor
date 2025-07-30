import torch
import torch.nn as nn
import pandas as pd
import os
import logging
from itertools import product
import json

from data_loader import load_mnist
from model_utils import build_mlp, get_optimizer
from train import train_model
from test import test_model

# ---------------- Configuration ----------------
device = torch.device("cpu")
# EPOCH = [1, 2, 4, 8]
# OPTIMIZER = ["adam", "sgd", "lbfgs"]
# HIDDEN_LAYER_COUNT = [1, 2, 3, 4]
# NODES_IN_HIDDEN_LAYER = [5, 10, 20, 30]
# BATCH_SIZE = [4, 8, 16, 32, 64, 128]

# ---------------- Logger Setup ----------------
LOG_DIR = "log"
LOG_FILE = os.path.join(LOG_DIR, "grid_search.log")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ---------------- Grid Search ----------------
def run_grid_search():
    combo_id = 0

    for epochs, opt_name, num_layers, num_nodes, batch_size in product(
        EPOCH, 
        OPTIMIZER,
        HIDDEN_LAYER_COUNT, 
        NODES_IN_HIDDEN_LAYER, 
        BATCH_SIZE
    ):
        combo_id += 1
        result_dir = f"results/comb_{combo_id}"
        os.makedirs(result_dir, exist_ok=True)

        logger.info(
            f"Running combination {combo_id} | epochs={epochs}, optimizer={opt_name}, "
            f"layers={num_layers}, nodes={num_nodes}, batch_size={batch_size}"
        )

        # Load data for this batch size
        train_loader, test_loader = load_mnist(batch_size = batch_size)

        # Build model and optimizer
        model = build_mlp(28 * 28, num_layers, num_nodes, 10).to(device)
        optimizer = get_optimizer(opt_name, model)
        criterion = nn.CrossEntropyLoss()

        # Train model
        train_logs = train_model(model, optimizer, criterion, train_loader, epochs, opt_name)

        # Test model
        test_result = test_model(model, test_loader, epochs - 1)
        test_logs = [test_result]

        # Save logs
        train_logs.to_csv(os.path.join(result_dir, "train.csv"), index=False)
        pd.DataFrame(test_logs).to_csv(os.path.join(result_dir, "test.csv"), index=False)

        # Save parameters
        params = {
            "epochs": epochs,
            "optimizer": opt_name,
            "hidden_layers": num_layers,
            "nodes_per_layer": num_nodes,
            "batch_size": batch_size
        }
        with open(os.path.join(result_dir, "params.json"), "w") as f:
            json.dump(params, f, indent=4)

        logger.info(f"Saved results for combination {combo_id} to '{result_dir}'")

# ---------------- Run ----------------
if __name__ == "__main__":
    run_grid_search()
