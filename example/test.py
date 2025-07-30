import torch
import time

def test_model(model, loader, epoch):
    """
    Tests the model on the test data and returns accuracy and evaluation time.
    """
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
