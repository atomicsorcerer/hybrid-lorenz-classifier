import torch
from torch.utils.data import random_split

from matplotlib import pyplot as plt
import polars as pl

from data import EventDataset

blur_size = 0.10
feature_cols = ["px_0", "py_0", "pz_0", "energy_0", "px_1", "py_1", "pz_1", "energy_1"]
data = EventDataset("../../data/background.csv",
                    "../../data/signal.csv",
                    feature_cols,
                    features_shape=(-1, 2, 4),
                    limit=20_000,
                    blur_data=True,
                    blur_size=blur_size,
                    shuffle_seed=314)

test_percent = 0.20
_, test_data = random_split(data, [1 - test_percent, test_percent], torch.Generator().manual_seed(314))
data = list(test_data)

X = []
Y = []
for x in test_data:
	X.append(x[0].tolist())
	Y.append(x[1].item())

X = torch.Tensor(X)
Y = torch.Tensor(Y).unsqueeze(1)

pfn_model = torch.load("model.pth")

# Analysis of weight identification function

pT = torch.sqrt(torch.add(torch.pow(X[..., 0][..., 0], 2), torch.pow(X[..., 1][..., 0], 2))).unsqueeze(1)
general_weight_result = pfn_model.weight_network(pT)[..., 0]
pT = pT.squeeze(1)

weight_coords = sorted(zip(pT.numpy(), general_weight_result.detach().numpy()), key=lambda x: x[0])

plt.plot(list(map(lambda x: x[0], weight_coords)), list(map(lambda x: x[1], weight_coords)))
plt.xlabel("pT")
plt.ylabel("General classifier proportion")
plt.title("Latent Space Pooled Hybrid Classifier - General classifier proportion vs. pT")
plt.show()

pT_vs_gen_prop_log = pl.DataFrame({
	"pT": list(map(lambda x: x[0], weight_coords)),
	"general classifier proportion": list(map(lambda x: x[1], weight_coords)),
	"classifier": "Latent Space Pooled Hybrid Classifier",
	"blur": blur_size
})
pT_vs_gen_prop_log.write_csv("weight_subnet_analysis.csv")

# Analysis of the accuracy/confidence of the classifier vs. pT

result = pfn_model(X)
result = torch.nn.functional.sigmoid(result)
acc = 1 - torch.abs(torch.subtract(result, Y)).squeeze()
acc = acc.tolist()
pT = torch.sqrt(torch.add(torch.pow(X[..., 0][..., 0], 2), torch.pow(X[..., 1][..., 0], 2)))
pT = pT.tolist()

coords = sorted(zip(pT, acc), key=lambda x: x[0])

plt.plot(list(map(lambda x: x[0], coords)), list(map(lambda x: x[1], coords)), marker="o", linestyle="", markersize=0.5)
plt.xlabel("pT")
plt.ylabel("Accuracy")
plt.title("Latent Space Pooled Hybrid Classifier - pT vs. accuracy")
plt.show()

pT_vs_acc_log = pl.DataFrame({
	"pT": list(map(lambda x: x[0], coords)),
	"acc": list(map(lambda x: x[1], coords)),
	"classifier": "Latent Space Pooled Hybrid Classifier",
	"blur": blur_size
})
pT_vs_acc_log.write_csv("pT_vs_acc_analysis.csv")
