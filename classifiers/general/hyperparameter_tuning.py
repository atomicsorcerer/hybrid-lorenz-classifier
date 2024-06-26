from sklearn.model_selection import GridSearchCV
from skorch import NeuralNetBinaryClassifier
import torch
from torch import nn, optim
from torch.utils.data import random_split

from data import EventDataset
from models import ParticleFlowNetwork

feature_cols = [
	"px_0", "py_0", "pz_0", "energy_0",
	"px_1", "py_1", "pz_1", "energy_1",
]
db = EventDataset("../../data/background.csv",
                  "../../data/signal.csv",
                  feature_cols,
                  features_shape=(-1, 2, 4),
                  limit=20_000)

test_percent = 0.10
training_data, testing_data = random_split(db, [1 - test_percent, test_percent])

X = []
Y = []
for x, y in training_data:
	X.append(x.numpy())
	Y.append(y)

X = torch.Tensor(X)
Y = torch.Tensor(Y)

model = NeuralNetBinaryClassifier(
	module=ParticleFlowNetwork,
	criterion=nn.BCEWithLogitsLoss,
	optimizer=optim.AdamW,
	max_epochs=10,
	module__input_size=4,
	module__total_feature_size=8,
)

param_grid = {
	"batch_size": [8, 16, 32, 64, 128],
	"module__classifier_hidden_layer_dimensions": [
		[128, 128, 128],
		[256, 256, 256],
		[256, 256, 128],
		[256, 128, 128],
		[512, 256, 128],
		[512, 512, 512],
	],
	"module__mapping_hidden_layer_dimensions": [
		[256, 256, 256],
		[256, 256, 128],
		[128, 128, 128],
		[256, 128, 128],
		[512, 256, 128],
	],
	"module__latent_space_dim": [2 ** i for i in range(8)],
	"optimizer__lr": [10 ** (-i) for i in range(8)]
}
grid = GridSearchCV(estimator=model, param_grid=param_grid, n_jobs=-1, cv=3)
grid_result = grid.fit(X, Y)

print(grid_result)
print(f"Best: {grid_result.best_score_} using {grid_result.best_params_}")