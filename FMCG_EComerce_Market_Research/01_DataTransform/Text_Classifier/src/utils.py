# import logging
import random
from typing import Dict, Any

import numpy as np
import torch
import yaml


def load_config(config_path: str) -> Dict[str, Any]:
    """Loads a YAML configuration file.

    Args:
        config_path (str): The path to the YAML configuration file.

    Returns:
        Dict[str, Any]: The configuration as a dictionary.
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def set_seed(seed: int) -> None:
    """Sets the random seed for reproducibility across libraries.

    Args:
        seed (int): The seed value to use.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        # The following two lines are for deterministic results on CUDA.
        # They can have a performance impact.
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
