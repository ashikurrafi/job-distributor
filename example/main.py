import torch
import torch.nn as nn
import pandas as pd
import os
import logging
import json
import argparse

from data_loader import load_mnist
from model_utils import build_mlp, get_optimizer
from train import train_model
from test import test_model

# ---------------- Logger Setup ----------------
def setup_logger(base_path):
    log_dir = os.path.join(base_path)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "info.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

# ---------------- Main Runner ----------------
def run_single_combination(epochs, optimizer_name, hidden_layers, nodes_per_layer, batch_size, base_path):
    device = torch.device("cpu")
    logger = setup_logger(base_path)

    result_dir = base_path
    os.makedirs(result_dir, exist_ok=True)

    logger.info(
        f"Running epochs={epochs}, optimizer={optimizer_name}, "
        f"layers={hidden_layers}, nodes={nodes_per_layer}, batch_size={batch_size}"
    )

    # Load data
    train_loader, test_loader = load_mnist(batch_size=batch_size)

    # Build model and optimizer
    model = build_mlp(28 * 28, hidden_layers, nodes_per_layer, 10).to(device)
    optimizer = get_optimizer(optimizer_name, model)
    criterion = nn.CrossEntropyLoss()

    # Train model
    train_logs = train_model(model, optimizer, criterion, train_loader, epochs, optimizer_name)

    # Test model once
    test_result = test_model(model, test_loader, epochs - 1)
    test_logs = [test_result]

    # Save logs
    train_logs.to_csv(os.path.join(result_dir, "train.csv"), index=False)
    pd.DataFrame(test_logs).to_csv(os.path.join(result_dir, "test.csv"), index=False)

    # Save parameters
    config = {
        "epochs": epochs,
        "optimizer": optimizer_name,
        "hidden_layers": hidden_layers,
        "nodes_per_layer": nodes_per_layer,
        "batch_size": batch_size
    }
    with open(os.path.join(result_dir, "params.json"), "w") as f:
        json.dump(config, f, indent=4)

    logger.info(f"Saved results to '{result_dir}'")

# ---------------- CLI ----------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a single hyperparameter configuration.")
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--optimizer", type=str, choices=["adam", "sgd", "lbfgs"], required=True)
    parser.add_argument("--hidden_layers", type=int, required=True)
    parser.add_argument("--nodes_per_layer", type=int, required=True)
    parser.add_argument("--batch_size", type=int, required=True)
    parser.add_argument("--base_path", type=str, required=True, help="Base path to store logs and results.")

    args = parser.parse_args()

    run_single_combination(
        epochs=args.epochs,
        optimizer_name=args.optimizer,
        hidden_layers=args.hidden_layers,
        nodes_per_layer=args.nodes_per_layer,
        batch_size=args.batch_size,
        base_path=args.base_path
    )
    
    
    
# python main.py \
#     --epochs 4 \
#     --optimizer adam \
#     --hidden_layers 2 \
#     --nodes_per_layer 10 \
#     --batch_size 32 \
#     --base_path ./experiment_runs

