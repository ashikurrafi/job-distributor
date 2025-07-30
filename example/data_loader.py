import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader, Subset

TRAIN_SIZE = 60000
TEST_SIZE = 10000

def load_mnist(train_size=TRAIN_SIZE, test_size=TEST_SIZE, batch_size=32):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])
    train_dataset = datasets.MNIST(root="./data", train=True, transform=transform, download=True)
    test_dataset = datasets.MNIST(root="./data", train=False, transform=transform, download=True)
    train_subset = Subset(train_dataset, list(range(train_size)))
    test_subset = Subset(test_dataset, list(range(test_size)))
    train_loader = DataLoader(train_subset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_subset, batch_size=batch_size)
    return train_loader, test_loader
