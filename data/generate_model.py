import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import sys
import traceback


# prep
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from sklearn.datasets import make_classification
from sklearn.preprocessing import binarize, LabelEncoder, MinMaxScaler

# models
from torch import nn
from torch import optim
from torch.autograd import Variable
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from demo.runners.support.utils import log_msg

async def generate_model():
    log_msg("COORDINATOR IS GENERATING THE INITIAL MODEL")

    # One Model
    model = nn.Sequential(
            nn.Linear(8, 4),
            nn.Sigmoid(),
            nn.Linear(4, 2),
            nn.Sigmoid(),
            nn.Linear(2, 1),
            nn.Sigmoid()
        )
    torch.save(model, "model/model.pt")

    return True
