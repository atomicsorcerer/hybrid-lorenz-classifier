import torch
from matplotlib import pyplot as plt
from torch.utils.data import DataLoader, random_split

from classifiers.utils import train, test
from models import WeightedHybridClassifier, LearnedWeightHybridClassifier
from data.event_dataset import EventDataset

feature_cols = [
	"px_0", "py_0", "pz_0", "energy_0",
	"px_1", "py_1", "pz_1", "energy_1",
]
data = EventDataset("../../data/background.csv",
                    "../../data/signal.csv",
                    feature_cols,
                    features_shape=(-1, 2, 4),
                    limit=20_000)

test_percent = 0.15
training_data, test_data = random_split(data, [1 - test_percent, test_percent])

batch_size = 64

train_dataloader = DataLoader(training_data, batch_size=batch_size, shuffle=True)
test_dataloader = DataLoader(test_data, batch_size=batch_size, shuffle=True)

model = LearnedWeightHybridClassifier(16,
                                      [128, 128],
                                      [512, 256, 128],
                                      [512, 256, 128],
                                      [128, 128])

loss_function = torch.nn.BCEWithLogitsLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)

epochs = 20
loss_over_time = []
accuracy_over_time = []
max_acc = 0.0
max_acc_epoch = 0
for t in range(epochs):
	print(f"Epoch {t + 1}\n-------------------------------")
	train(train_dataloader, model, loss_function, optimizer, True)
	loss, acc = test(test_dataloader, model, loss_function, True)
	
	loss_over_time.append(loss)
	accuracy_over_time.append(acc)
	
	if acc > max_acc:
		torch.save(model, "model.pth")
		max_acc = acc
		max_acc_epoch = t + 1

print("Finished Training")
print(f"Model saved had {max_acc * 100:<0.2f}% accuracy, and was from epoch {max_acc_epoch}.")

plt.plot(accuracy_over_time[0:max_acc_epoch])
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.title("Learned Weight Hybrid Classifier Accuracy per Epoch")
plt.show()
