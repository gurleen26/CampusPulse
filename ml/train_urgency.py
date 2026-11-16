"""Train the complaint URGENCY classifier.   Run:  python -m ml.train_urgency"""
from config import URGENCY_LEVELS
from ml.trainer import train_target


def train(verbose=True):
    return train_target("urgency", URGENCY_LEVELS, "urgency", verbose)


if __name__ == "__main__":
    train()
