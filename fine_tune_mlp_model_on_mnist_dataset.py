import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset
from itertools import product
import time
import pandas as pd
import os
import logging

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

# ---------------- Configuration ----------------
device = torch.device("cpu")

EPOCHS_LIST = [1, 2, 4, 8]
OPTIMIZERS_LIST = ["adam", "sgd", "lbfgs"]
HIDDEN_LAYERS_LIST = [1, 2, 3, 4]
NODES_IN_HIDDEN_LAYERS_LIST = [5, 10, 20, 30]
BATCH_SIZE = 64
TRAIN_SIZE = 6000
TEST_SIZE = 1000

# ---------------- Data ----------------
def load_mnist(train_size=TRAIN_SIZE, test_size=TEST_SIZE):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])
    train_dataset = datasets.MNIST(root="./data", train=True, transform=transform, download=True)
    test_dataset = datasets.MNIST(root="./data", train=False, transform=transform, download=True)

    train_subset = Subset(train_dataset, list(range(train_size)))
    test_subset = Subset(test_dataset, list(range(test_size)))

    train_loader = DataLoader(train_subset, batch_size=BATCH_SIZE, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=BATCH_SIZE)
    return train_loader, test_loader

# ---------------- Model Builder ----------------
def build_mlp(input_dim, hidden_layers, nodes, output_dim):
    layers = []
    dim = input_dim
    for _ in range(hidden_layers):
        layers.append(nn.Linear(dim, nodes))
        layers.append(nn.ReLU())
        dim = nodes
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

def evaluate_model(model, loader, epoch):
    model.eval()
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
    return {
        "epoch": epoch + 1,
        "accuracy": round(accuracy, 4),
        "elapsed_time": round(elapsed, 4)
    }

# ---------------- Grid Search ----------------
def run_grid_search():
    train_loader, test_loader = load_mnist()
    combo_id = 0

    for epochs, opt_name, hl, nodes in product(EPOCHS_LIST, OPTIMIZERS_LIST, HIDDEN_LAYERS_LIST, NODES_IN_HIDDEN_LAYERS_LIST):
        combo_id += 1
        result_dir = f"results/comb_{combo_id}"
        os.makedirs(result_dir, exist_ok=True)

        logger.info(f"🔍 Running combo {combo_id} | epochs={epochs}, optimizer={opt_name}, layers={hl}, nodes={nodes}")

        model = build_mlp(28*28, hl, nodes, 10).to(device)
        optimizer = get_optimizer(opt_name, model)
        criterion = nn.CrossEntropyLoss()

        train_logs = train_model(model, optimizer, criterion, train_loader, epochs, opt_name)

        test_logs = []
        for epoch in range(epochs):
            result = evaluate_model(model, test_loader, epoch)
            test_logs.append(result)

        # Save logs as CSV
        train_logs.to_csv(os.path.join(result_dir, "train.csv"), index=False)
        pd.DataFrame(test_logs).to_csv(os.path.join(result_dir, "test.csv"), index=False)

        logger.info(f"✅ Saved results for combo {combo_id} to '{result_dir}'")

# ---------------- Run ----------------
if __name__ == "__main__":
    run_grid_search()
