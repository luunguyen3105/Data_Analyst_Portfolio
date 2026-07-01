import lightning as L
import torch
import torch.nn as nn
from torch.optim import AdamW
from torchmetrics import Accuracy, F1Score, MetricCollection, Precision, Recall

from src.models.classifier import TextClassifier


class TextClassifierModule(L.LightningModule):
    def __init__(
        self,
        embedding_dim: int,
        num_classes: int,
        dropout: float,
        learning_rate: float,
        config: dict,
        loss_fn: nn.Module = None,
        weight_decay: float = 1e-2,
    ):
        super().__init__()
        self.save_hyperparameters(ignore=["loss_fn"])
        self.model = TextClassifier(
            embedding_dim=embedding_dim,
            num_classes=num_classes,
            dropout=dropout,
        )
        self.loss_fn = loss_fn
        self.weight_decay = weight_decay
        self.learning_rate = learning_rate

        task = "multiclass"
        metrics = MetricCollection(
            [
                Accuracy(task=task, num_classes=num_classes, average="macro"),
                Precision(task=task, num_classes=num_classes, average="macro"),
                Recall(task=task, num_classes=num_classes, average="macro"),
                F1Score(task=task, num_classes=num_classes, average="macro"),
            ]
        )
        self.train_metrics = metrics.clone(prefix="train_")
        self.val_metrics = metrics.clone(prefix="val_")
        self.test_metrics = metrics.clone(prefix="test_")

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        return self.model(embeddings)

    def _shared_step(self, batch: tuple) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        embeddings, labels = batch
        logits = self.forward(embeddings)
        loss = self.loss_fn(logits, labels)
        return loss, logits, labels

    def training_step(self, batch: tuple, batch_idx: int) -> torch.Tensor:
        loss, logits, labels = self._shared_step(batch)
        self.log("train_loss", loss, on_step=True, on_epoch=True, prog_bar=True, logger=True)
        self.train_metrics.update(logits, labels)
        self.log_dict(self.train_metrics, on_step=False, on_epoch=True)
        return loss

    def validation_step(self, batch: tuple, batch_idx: int):
        loss, logits, labels = self._shared_step(batch)
        self.log("val_loss", loss, on_step=False, on_epoch=True, prog_bar=True, logger=True)
        self.val_metrics.update(logits, labels)
        self.log_dict(self.val_metrics, on_step=False, on_epoch=True)

    def test_step(self, batch: tuple, batch_idx: int):
        loss, logits, labels = self._shared_step(batch)
        self.log("test_loss", loss, on_step=False, on_epoch=True, logger=True)
        self.test_metrics.update(logits, labels)
        self.log_dict(self.test_metrics, on_step=False, on_epoch=True)

    def configure_optimizers(self) -> torch.optim.Optimizer:
        return AdamW(self.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay)
