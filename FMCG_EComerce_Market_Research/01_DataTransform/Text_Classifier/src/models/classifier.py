import torch
import torch.nn as nn
from typing import List, Dict

from .embedders import BaseEmbedder


class TextClassifier(nn.Module):
    """
    A text classification model composed of a pretrained embedder and a classification head.
    """

    def __init__(self, embedding_dim: int, num_classes: int, dropout: float = 0.1):
        """
        Initializes the TextClassifier.

        Args:
            embedding_dim (int): The dimension of the input embeddings.
            num_classes (int): The number of output classes.
            dropout (float): The dropout probability for the classification head.
        """
        super().__init__()
        self.num_classes = num_classes

        # self.classifier_head = nn.Sequential(
        #     nn.Linear(embedding_dim, 512),
        #     nn.ReLU(),
        #     nn.Dropout(dropout),
        #     nn.Linear(512, 256),
        #     nn.ReLU(),
        #     nn.Dropout(dropout),
        #     nn.Linear(256, num_classes)
        # )
        # self.classifier_head = nn.Sequential(
        #     nn.Linear(embedding_dim, embedding_dim // 2),
        #     nn.ReLU(),
        #     nn.Dropout(dropout),
        #     nn.Linear(embedding_dim // 2, 512),
        #     nn.ReLU(),
        #     nn.Dropout(dropout),
        #     nn.Linear(512, num_classes)
        # )
        self.classifier_head = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(embedding_dim // 2, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        """
        Performs a forward pass through the model.

        Args:
            embeddings (torch.Tensor): A batch of pre-computed embeddings.

        Returns:
            torch.Tensor: The output logits from the classification head.
        """
        # Ensure embeddings are on the same device and dtype as the classifier head
        model_param = next(self.classifier_head.parameters())
        device = model_param.device
        dtype = model_param.dtype
        embeddings = embeddings.to(device=device, dtype=dtype)

        logits = self.classifier_head(embeddings)
        return logits
