import lightning as L
from torch.utils.data import DataLoader
from typing import TYPE_CHECKING, Dict

from helper.logger_helper import LoggerSimple
from src.data_loader import create_data_loaders

if TYPE_CHECKING:
    from src.models.embedders import BaseEmbedder

logger = LoggerSimple(name=__name__).logger


class TextDataModule(L.LightningDataModule):
    def __init__(
        self,
        file_path: str,
        embedder: "BaseEmbedder",
        label_to_id: Dict[str, int],
        batch_size: int,
        seed: int,
        min_label_count: int,
        max_label_count: int,
        max_length: int,
    ):
        super().__init__()
        self.file_path = file_path
        self.embedder = embedder
        self.label_to_id = label_to_id
        self.batch_size = batch_size
        self.min_label_count = min_label_count
        self.max_label_count = max_label_count
        self.seed = seed
        self.max_length = max_length
        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None

    def setup(self, stage: str = None):
        if self.train_dataset is None:
            logger.info(f"Loading data stage={stage} from {self.file_path}...")
            train_loader, val_loader, test_loader = create_data_loaders(
                file_path=self.file_path,
                embedder=self.embedder,
                label_to_id=self.label_to_id,
                batch_size=self.batch_size,
                seed=self.seed,
                min_label_count=self.min_label_count,
                max_label_count=self.max_label_count,
                max_length=self.max_length,
            )
            self.train_dataset = train_loader.dataset
            self.val_dataset = val_loader.dataset
            self.test_dataset = test_loader.dataset

    def train_dataloader(self) -> DataLoader:
        return DataLoader(self.train_dataset, batch_size=self.batch_size, shuffle=True)

    def val_dataloader(self) -> DataLoader:
        return DataLoader(self.val_dataset, batch_size=self.batch_size, shuffle=False)

    def test_dataloader(self) -> DataLoader:
        return DataLoader(self.test_dataset, batch_size=self.batch_size, shuffle=False)
