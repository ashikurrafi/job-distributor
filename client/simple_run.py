import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset
import argparse
import pandas as pd
import time
import os
import json
import logging

# ---------------- Argument Parser ----------------
parser = argparse.ArgumentParser()
parser.add_argument("--job_id", type=int, required=True)
parser.add_argument("--expId", type=str, required=True)
parser.add_argument("--epochs", type=int, required=True)
parser.add_argument("--optimizer", choices=["adam", "sgd", "lbfgs"], required=True)
parser.add_argument("--hidden_layers", type=int, required=True)
parser.add_argument("--nodes_in_hidden_layers", type=int, required=True)
args = parser.parse_args()

# ---------------- Logger Setup ----------------
LOG_DIR = f"{args.expId}/logs"
LOG_FILE = os.path.join(LOG_DIR, f"job_{args.job_id}.log")
os.makedirs(LOG_DIR, exist_ok=True)

RESULT_DIR = f"{args.expId}/results/job_{args.job_id}"
os.makedirs(RESULT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------- Config ----------------
device = torch.device("cpu")
BATCH_SIZE = 64
TRAIN_SIZE = 60000
TEST_SIZE = 10000

# Save config to JSON
config_path = os.path.join(RESULT_DIR, "params.json")
with open(config_path, "w") as f:
    json.dump(vars(args), f, indent=4)

# ---------------- Data ----------------
def load_mnist(train_size=TRAIN_SIZE, test_size=TEST_SIZE):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    if not os.path.exists("./data/MNIST/processed/training.pt"):
        logger.info("🔽 Downloading MNIST...")
        datasets.MNIST(root="./data", train=True, download=True)
        datasets.MNIST(root="./data", train=False, download=True)

    train_dataset = datasets.MNIST(root="./data", train=True, transform=transform, download=False)
    test_dataset = datasets.MNIST(root="./data", train=False, transform=transform, download=False)

    train_subset = Subset(train_dataset, list(range(train_size)))
    test_subset = Subset(test_dataset, list(range(test_size)))

    train_loader = DataLoader(train_subset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=BATCH_SIZE)
    return train_loader, test_loader

# ---------------- Model Builder ----------------
def build_mlp(input_dim, hidden_layers, nodes_in_hidden_layers, output_dim):
    layers = []
    dim = input_dim
    for _ in range(hidden_layers):
        layers.append(nn.Linear(dim, nodes_in_hidden_layers))
        layers.append(nn.ReLU())
        dim = nodes_in_hidden_layers
    layers.append(nn.Linear(dim, output_dim))
    return nn.Sequential(*layers)

def get_optimizer(name, model):
    if name == "adam":
        return optim.Adam(model.parameters(), lr=0.01)
    elif name == "sgd":
        return optim.SGD(model.parameters(), lr=0.01)
    elif name == "lbfgs":
        return optim.LBFGS(model.parameters(), lr=0.01)
    else:
        raise ValueError(f"Unknown optimizer: {name}")

# ---------------- Training & Evaluation ----------------
def train_model(model, optimizer, criterion, loader, epochs, opt_name):
    model.train()
    logs = []
    iter_count = 0
    for epoch in range(epochs):
        for X, y in loader:
            start = time.time()
            X, y = X.view(X.size(0), -1), y

            if opt_name == "lbfgs":
                def closure():
                    optimizer.zero_grad()
                    output = model(X)
                    loss = criterion(output, y)
                    loss.backward()
                    return loss
                loss = optimizer.step(closure)
                loss_value = loss.item()
            else:
                optimizer.zero_grad()
                output = model(X)
                loss = criterion(output, y)
                loss.backward()
                optimizer.step()
                loss_value = loss.item()

            elapsed = time.time() - start
            iter_count += 1
            logs.append({
                "iteration": iter_count,
                "loss": round(loss_value, 4),
                "elapsed_time": round(elapsed, 4)
            })
    return pd.DataFrame(logs)

def evaluate_model(model, loader, epochs):
    model.eval()
    logs = []
    for epoch in range(epochs):
        correct, total = 0, 0
        start = time.time()
        with torch.no_grad():
            for X, y in loader:
                X = X.view(X.size(0), -1)
                output = model(X)
                preds = torch.argmax(output, dim=1)
                correct += (preds == y).sum().item()
                total += y.size(0)
        accuracy = correct / total
        elapsed = time.time() - start
        logs.append({
            "epoch": epoch + 1,
            "accuracy": round(accuracy, 4),
            "elapsed_time": round(elapsed, 4)
        })
    return pd.DataFrame(logs)

# ---------------- Main ----------------
def main():
    logger.info(f"🚀 Job {args.job_id} started")
    logger.info(f"📌 Config: {vars(args)}")

    train_loader, test_loader = load_mnist()

    model = build_mlp(28*28, args.hidden_layers, args.nodes_in_hidden_layers, 10).to(device)
    optimizer = get_optimizer(args.optimizer, model)
    criterion = nn.CrossEntropyLoss()

    logger.info("🧠 Training started...")
    train_logs = train_model(model, optimizer, criterion, train_loader, args.epochs, args.optimizer)
    train_logs.to_csv(os.path.join(RESULT_DIR, "train.csv"), index=False)

    logger.info("🧪 Evaluating...")
    test_logs = evaluate_model(model, test_loader, args.epochs)
    test_logs.to_csv(os.path.join(RESULT_DIR, "test.csv"), index=False)

    logger.info(f"✅ Job {args.job_id} completed successfully. Results saved to '{RESULT_DIR}'")

if __name__ == "__main__":
    start_time = time.time()

    main()
    
    logger.info(f"total time: {time.time() - start_time}s")