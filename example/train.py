import pandas as pd
import time

def train_model(model, optimizer, criterion, loader, epochs, opt_name):
    """
    Trains the given model using the specified optimizer and loss criterion.
    Returns a DataFrame containing loss and timing logs per iteration.
    """
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
