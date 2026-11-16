"""Train the complaint CATEGORY classifier.   Run:  python -m ml.train_category"""
from config import CATEGORIES
from ml.trainer import train_target


def train(verbose=True):
    return train_target("category", CATEGORIES, "category", verbose)


if __name__ == "__main__":
    train()
