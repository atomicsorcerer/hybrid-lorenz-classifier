import torch
from torch import nn

from classifiers.general import ParticleFlowNetwork, ParticleMapping
from classifiers.invariant import LorenzInvariantNetwork


class WeightedHybridClassifier(nn.Module):
	def __init__(self,
	             invariant_network_weight: float,
	             latent_space_dim: int,
	             pfn_mapping_hidden_layer_dimensions: list[int],
	             pfn_classifier_hidden_layer_dimensions: list[int],
	             lorenz_invariant_hidden_layer_dimensions: list[int]
	             ):
		"""
		Classifier that combines the result of two subnets using a weighted average.
		
		Args:
			invariant_network_weight: The weight on the invariant network result.
			latent_space_dim: Latent space dimension for the PFN general classifier.
			pfn_mapping_hidden_layer_dimensions: Hidden layers for the PFN mapping module.
			pfn_classifier_hidden_layer_dimensions: Hidden layers for the PFN general classifier.
			lorenz_invariant_hidden_layer_dimensions: Hidden layers for the Lorentz-invariant classifier.
		
		Raises:
			ValueError: Classifier weights must be between 0 and 1.
		"""
		super().__init__()
		
		self.general_p_map = ParticleFlowNetwork(4,
		                                         8,
		                                         latent_space_dim,
		                                         pfn_classifier_hidden_layer_dimensions,
		                                         pfn_mapping_hidden_layer_dimensions)
		
		self.invariant_p_map = LorenzInvariantNetwork(1, lorenz_invariant_hidden_layer_dimensions)
		
		if invariant_network_weight > 1 or invariant_network_weight < 0:
			raise ValueError("Classifier weights must be between 0 and 1.")
		
		self.invariant_network_weight = invariant_network_weight
		self.general_network_weight = 1.0 - invariant_network_weight
	
	def forward(self, x):
		general_result = self.general_p_map(x)
		invariant_result = self.invariant_p_map(x)
		
		combined_result = (torch.mul(general_result, self.general_network_weight)
		                   + torch.mul(invariant_result, self.invariant_network_weight))
		
		return combined_result


class LearnedWeightHybridClassifier(nn.Module):
	def __init__(self,
	             latent_space_dim: int,
	             pfn_mapping_hidden_layer_dimensions: list[int],
	             pfn_classifier_hidden_layer_dimensions: list[int],
	             lorenz_invariant_hidden_layer_dimensions: list[int],
	             weight_network_hidden_layer_dimensions: list[int]
	             ):
		"""
		Classifier that combines the result of two subnets using a weighted average.

		Args:
			latent_space_dim: Latent space dimension for the PFN general classifier.
			pfn_mapping_hidden_layer_dimensions: Hidden layers for the PFN mapping module.
			pfn_classifier_hidden_layer_dimensions: Hidden layers for the PFN general classifier.
			lorenz_invariant_hidden_layer_dimensions: Hidden layers for the Lorentz-invariant classifier.
			weight_network_hidden_layer_dimensions: Hidden layers for the weight network classifier.

		Raises:
			ValueError: Classifier weights must be between 0 and 1.
			ValueError: Length of weight_network_hidden_layer_dimensions cannot be zero.
		"""
		super().__init__()
		
		self.general_p_map = ParticleFlowNetwork(4,
		                                         8,
		                                         latent_space_dim,
		                                         pfn_classifier_hidden_layer_dimensions,
		                                         pfn_mapping_hidden_layer_dimensions)
		
		self.invariant_p_map = LorenzInvariantNetwork(1, lorenz_invariant_hidden_layer_dimensions)
		
		if len(weight_network_hidden_layer_dimensions) == 0:
			raise ValueError("Length of weight_network_hidden_layer_dimensions cannot be zero.")
		
		stack = nn.Sequential(ParticleMapping(4, 8, latent_space_dim, pfn_mapping_hidden_layer_dimensions),
		                      nn.Linear(latent_space_dim, weight_network_hidden_layer_dimensions[0]),
		                      nn.BatchNorm1d(weight_network_hidden_layer_dimensions[0]),
		                      nn.ReLU())
		
		for i in range(len(weight_network_hidden_layer_dimensions)):
			stack.append(
				nn.Linear(weight_network_hidden_layer_dimensions[i],
				          weight_network_hidden_layer_dimensions[i] if i == len(
					          weight_network_hidden_layer_dimensions) - 1 else
				          weight_network_hidden_layer_dimensions[i + 1]))
			stack.append(nn.BatchNorm1d(
				weight_network_hidden_layer_dimensions[i] if i == len(weight_network_hidden_layer_dimensions) - 1 else
				weight_network_hidden_layer_dimensions[i + 1]))
			stack.append(nn.ReLU())
		
		stack.append(nn.Linear(weight_network_hidden_layer_dimensions[-1], 2))
		stack.append(nn.Softmax(dim=1))
		
		self.stack = stack
	
	def forward(self, x):
		general_result = self.general_p_map(x)
		invariant_result = self.invariant_p_map(x)
		
		network_weights = self.stack(x)
		general_weight = network_weights[..., 0].unsqueeze(1)
		invariant_weight = network_weights[..., 1].unsqueeze(1)
		
		combined_result = (torch.mul(general_result, general_weight)
		                   + torch.mul(invariant_result, invariant_weight))
		
		return combined_result


class LatentSpacePooledHybridClassifier(nn.Module):
	def __init__(self,
	             latent_space_dim: int,
	             pfn_mapping_hidden_layer_dimensions: list[int],
	             lorenz_invariant_hidden_layer_dimensions: list[int],
	             weight_network_hidden_layer_dimensions: list[int],
	             classifier_hidden_layer_dimensions: list[int],
	             general_classifier_preference: float | None = None
	             ):
		"""
		Classifier that combines the result of two subnets using a weighted average.

		Args:
			latent_space_dim: Latent space dimension for the PFN general classifier.
			pfn_mapping_hidden_layer_dimensions: Hidden layers for the PFN mapping module.
			lorenz_invariant_hidden_layer_dimensions: Hidden layers for the Lorentz-invariant classifier.
			weight_network_hidden_layer_dimensions: Hidden layers for the weight network classifier.
			classifier_hidden_layer_dimensions: Hidden layers for the classifier MLP.

		Raises:
			ValueError: Classifier weights must be between 0 and 1.
			ValueError: Length of weight_network_hidden_layer_dimensions cannot be zero.
		"""
		super().__init__()
		
		self.general_p_map = ParticleMapping(4,
		                                     8,
		                                     latent_space_dim,
		                                     pfn_mapping_hidden_layer_dimensions)
		
		self.invariant_p_map = LorenzInvariantNetwork(latent_space_dim, lorenz_invariant_hidden_layer_dimensions)
		
		if len(weight_network_hidden_layer_dimensions) == 0:
			raise ValueError("Length of weight_network_hidden_layer_dimensions cannot be zero.")
		
		weight_network = nn.Sequential(nn.Linear(1, weight_network_hidden_layer_dimensions[0]),
		                               nn.BatchNorm1d(weight_network_hidden_layer_dimensions[0]),
		                               nn.ReLU())
		
		for i in range(len(weight_network_hidden_layer_dimensions)):
			weight_network.append(
				nn.Linear(weight_network_hidden_layer_dimensions[i],
				          weight_network_hidden_layer_dimensions[i] if i == len(
					          weight_network_hidden_layer_dimensions) - 1 else
				          weight_network_hidden_layer_dimensions[i + 1]))
			weight_network.append(nn.BatchNorm1d(
				weight_network_hidden_layer_dimensions[i] if i == len(weight_network_hidden_layer_dimensions) - 1 else
				weight_network_hidden_layer_dimensions[i + 1]))
			weight_network.append(nn.ReLU())
		
		weight_network.append(nn.Linear(weight_network_hidden_layer_dimensions[-1], 2))
		weight_network.append(nn.Softmax(dim=1))
		
		stack = nn.Sequential(nn.Linear(latent_space_dim, classifier_hidden_layer_dimensions[0]),
		                      nn.BatchNorm1d(classifier_hidden_layer_dimensions[0]),
		                      nn.ReLU())
		
		for i in range(len(classifier_hidden_layer_dimensions)):
			stack.append(
				nn.Linear(classifier_hidden_layer_dimensions[i],
				          classifier_hidden_layer_dimensions[i] if i == len(classifier_hidden_layer_dimensions) - 1 else
				          classifier_hidden_layer_dimensions[i + 1]))
			stack.append(nn.BatchNorm1d(
				classifier_hidden_layer_dimensions[i] if i == len(classifier_hidden_layer_dimensions) - 1 else
				classifier_hidden_layer_dimensions[i + 1]))
			stack.append(nn.ReLU())
		
		stack.append(nn.Linear(classifier_hidden_layer_dimensions[-1], 1))
		
		self.weight_network = weight_network
		self.general_classifier_preference = general_classifier_preference
		self.stack = stack
		self.avg_pool_2d = nn.AvgPool2d((2, 1))
	
	def forward(self, x):
		general_result = self.general_p_map(x)
		invariant_result = self.invariant_p_map(x)
		combined_result = torch.stack((general_result, invariant_result), dim=1)
		
		pT = torch.sqrt(torch.add(torch.pow(x[..., 0][..., 0], 2), torch.pow(x[..., 1][..., 0], 2))).unsqueeze(1)
		pool_weights = self.weight_network(pT).reshape(-1, 2, 1)
		
		if self.general_classifier_preference is not None:
			skew_weights = torch.Tensor([
				[1 - self.general_classifier_preference],
				[1 - self.general_classifier_preference]
			])
			pool_weights = torch.mul(pool_weights, skew_weights)
			pool_weights = torch.add(pool_weights, torch.Tensor([[self.general_classifier_preference], [0.0]]))
		
		combined_result = torch.mul(combined_result, pool_weights)
		combined_result = self.sum_pool_2d(combined_result)
		combined_result = self.stack(combined_result)
		
		return combined_result
	
	def sum_pool_2d(self, x: torch.Tensor) -> torch.Tensor:
		"""
		Performs sum pooling operation.

		Args:
			x: Input tensor(s).

		Returns:
			torch.Tensor: Output tensor with predefined output dimensions.
		"""
		x = self.avg_pool_2d(x)
		x = torch.mul(x, 2)
		x = x.squeeze()
		
		return x
