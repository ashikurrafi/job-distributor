import torch.nn as nn
import torch.optim as optim

def build_mlp(input_dim, hidden_layers, nodes, output_dim):
    """
    Constructs a feedforward neural network (MLP) with the given parameters.
    """
    layers = []
    dim = input_dim
    for _ in range(hidden_layers):
        layers.append(nn.Linear(dim, nodes))
        layers.append(nn.ReLU())
        dim = nodes
    layers.append(nn.Linear(dim, output_dim))
    return nn.Sequential(*layers)

def get_optimizer(name, model, lr=0.01):
    """
    Returns an optimizer given its name and the model's parameters.
    """
    if name == "adam":
        return optim.Adam(model.parameters(), lr=lr)
    elif name == "sgd":
        return optim.SGD(model.parameters(), lr=lr)
    elif name == "lbfgs":
        return optim.LBFGS(model.parameters(), lr=lr)
    else:
        raise ValueError(f"Unknown optimizer: {name}")