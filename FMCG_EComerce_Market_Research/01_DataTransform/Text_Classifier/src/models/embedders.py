from abc import ABC, abstractmethod
from typing import List, Union, Optional
import gc
import numpy as np
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
from FlagEmbedding import BGEM3FlagModel
from tqdm import tqdm
from llama_cpp import Llama


class BaseEmbedder(ABC):
    """Abstract base class for all embedding models."""

    def __init__(self, model_name: str, device: str = None):
        """
        Initializes the BaseEmbedder.

        Args:
            model_name (str): The name or path of the model to load.
            device (str, optional): The device to run the model on ('cpu' or 'cuda'). 
                                    If None, will use CUDA if available, otherwise CPU.
        """
        self.model_name = model_name
        self.device = device if device else ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model()

    def _free_memory(self):
        """Free up GPU memory after processing."""
        if self.device == 'cuda':
            torch.cuda.empty_cache()
            gc.collect()

    @abstractmethod
    def _load_model(self):
        """Loads the specific embedding model."""
        pass

    @abstractmethod
    def encode(self, texts: List[str], batch_size: int = None, max_length: int = 300,
               use_fp16: bool = False) -> torch.Tensor:
        """
        Encodes a list of texts into embeddings.

        Args:
            texts (List[str]): The list of texts to encode.
            batch_size (int, optional): Batch size for processing. If None, default batch size is used.
            max_length (int, optional): Maximum length of input text tokens. Default is 300.
            use_fp16 (bool, optional): Whether to use FP16 precision to reduce memory usage. Default is False.

        Returns:
            torch.Tensor: A tensor of shape (n_texts, embedding_dim) moved to CPU memory.
        """
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Returns the embedding dimension of the model."""
        pass


class SentenceTransformerEmbedder(BaseEmbedder):
    """Embedder for models from the sentence-transformers library."""

    def _load_model(self):
        """Loads a SentenceTransformer model."""
        return SentenceTransformer(self.model_name, device=self.device)

    def encode(self, texts: List[str], batch_size: int = 32, max_length: int = 300,
               use_fp16: bool = False) -> torch.Tensor:
        """Encodes texts using the SentenceTransformer model.
        
        Args:
            texts (List[str]): The list of texts to encode
            batch_size (int, optional): Batch size for processing. Default is 32.
            max_length (int, optional): Maximum length of input text tokens. Default is 300.
            use_fp16 (bool, optional): Whether to use FP16 precision. Default is False.
            
        Returns:
            torch.Tensor: A tensor of shape (n_texts, embedding_dim) moved to CPU memory.
        """
        # Use half precision if requested and GPU is available
        fp16_context = torch.cuda.amp.autocast() if use_fp16 and self.device == 'cuda' else torch.no_grad()

        with fp16_context:
            embeddings = self.model.encode(
                texts,
                convert_to_tensor=True,
                device=self.device,
                batch_size=batch_size,
                max_length=max_length,
                show_progress_bar=True
            )

        # Move the result to CPU to free up GPU memory
        result = embeddings.cpu()
        self._free_memory()
        return result

    @property
    def embedding_dim(self) -> int:
        """Returns the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()


class BGEM3Embedder(BaseEmbedder):
    """Embedder for the BAAI/bge-m3 model."""

    def _load_model(self):
        """Loads the BGEM3FlagModel."""
        # Note: BGEM3FlagModel handles device placement internally
        # but we'll ensure it uses the correct device and fp16 when available
        use_cuda = self.device == 'cuda'
        return BGEM3FlagModel(self.model_name, use_fp16=use_cuda and torch.cuda.is_available())

    def encode(self, texts: List[str], batch_size: int = 32, max_length: int = 300,
               use_fp16: bool = True) -> torch.Tensor:
        """Encodes texts using the BGEM3FlagModel with optional batching.
        
        Args:
            texts (List[str]): The list of texts to encode
            batch_size (int, optional): Batch size for processing. Default is 32.
            max_length (int, optional): Maximum length of input text tokens. Default is 300.
            use_fp16 (bool, optional): Whether to use FP16 precision. Default is True.
            
        Returns:
            torch.Tensor: A tensor of shape (n_texts, embedding_dim) moved to CPU memory.
        """
        # Always process in batches for better memory management
        if batch_size is None:
            # Use a reasonable default if None is specified
            batch_size = 32

        # Process texts in batches with progress bar
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        # BGEM3 already handles fp16 internally based on the model initialization
        for i in tqdm(range(0, len(texts), batch_size), desc="Encoding texts with BGE-M3", total=total_batches):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(
                batch_texts,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
                max_length=max_length
            )['dense_vecs']

            # Convert numpy to torch tensor
            batch_tensor = torch.from_numpy(batch_embeddings)
            all_embeddings.append(batch_tensor)

            # Explicitly clear GPU cache after each batch if using CUDA
            if self.device == 'cuda':
                torch.cuda.empty_cache()

        # Combine all batch embeddings and ensure they're on CPU
        result = torch.cat(all_embeddings, dim=0)
        self._free_memory()
        return result

    @property
    def embedding_dim(self) -> int:
        """Returns the embedding dimension."""
        return 1024  # BGE-M3 has a fixed dimension of 1024


class HFTransformerEmbedder(BaseEmbedder):
    """Embedder for models from the Hugging Face transformers library."""

    def _load_model(self):
        """Loads a model and tokenizer from Hugging Face."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModel.from_pretrained(self.model_name)
        return model.to(self.device)

    def _mean_pooling(self, model_output, attention_mask):
        """Performs mean pooling on token embeddings."""
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def encode(self, texts: List[str], batch_size: int = 32, max_length: int = 300,
               use_fp16: bool = False) -> torch.Tensor:
        """Encodes texts using a Hugging Face transformer model.
        
        Args:
            texts (List[str]): The list of texts to encode
            batch_size (int, optional): Batch size for processing. Default is 32.
            max_length (int, optional): Maximum length of input text tokens. Default is 300.
            use_fp16 (bool, optional): Whether to use FP16 precision. Default is False.
            
        Returns:
            torch.Tensor: A tensor of shape (n_texts, embedding_dim) moved to CPU memory.
        """
        # Always use batching for consistent memory handling
        if batch_size is None:
            batch_size = 32

        # Initialize context manager for mixed precision if requested
        fp16_context = torch.cuda.amp.autocast() if use_fp16 and self.device == 'cuda' else torch.no_grad()

        # Process texts in batches with tqdm progress bar
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in tqdm(range(0, len(texts), batch_size), desc="Encoding texts with HF Transformer", total=total_batches):
            batch_texts = texts[i:i + batch_size]

            # Tokenize and move to device
            encoded_input = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors='pt'
            ).to(self.device)

            # Process with appropriate precision
            with fp16_context:
                model_output = self.model(**encoded_input)

            # Apply pooling and normalization
            batch_embeddings = self._mean_pooling(model_output, encoded_input['attention_mask'])
            batch_embeddings = F.normalize(batch_embeddings, p=2, dim=1)

            # Move embeddings to CPU immediately to free GPU memory
            all_embeddings.append(batch_embeddings.cpu())

            # Clear GPU cache after each batch
            if self.device == 'cuda':
                torch.cuda.empty_cache()

        # Combine all batch embeddings (already on CPU)
        result = torch.cat(all_embeddings, dim=0)
        self._free_memory()
        return result

    @property
    def embedding_dim(self) -> int:
        """Returns the embedding dimension."""
        return self.model.config.hidden_size


class GGUFEmbedder(BaseEmbedder):
    """Embedder for GGUF models using llama-cpp-python."""

    def __init__(self, model_name: str, model_filename: str, device: str = None):
        """
        Initializes the GGUFEmbedder.

        Args:
            model_name (str): The name or path of the model repo to load from.
            model_filename (str): The specific .gguf file to use from the repo.
            device (str, optional): The device to run the model on ('cpu' or 'cuda').
                                    If None, will use CUDA if available, otherwise CPU.
        """
        self.model_filename = model_filename
        super().__init__(model_name, device)

    def _load_model(self):
        """Loads a GGUF model from a Hugging Face repo."""
        n_gpu_layers = -1 if self.device == 'cuda' else 0
        try:
            return Llama.from_pretrained(
                repo_id=self.model_name,
                filename=self.model_filename,
                embedding=True,
                verbose=False,
                n_gpu_layers=n_gpu_layers
            )
        except Exception as e:
            raise IOError(f"Failed to load GGUF model '{self.model_name}' with file '{self.model_filename}'. "
                          f"Ensure 'llama-cpp-python' is installed and the model is accessible. Error: {e}")

    def encode(self, texts: List[str], batch_size: int = 32, max_length: int = 300,
               use_fp16: bool = False) -> torch.Tensor:
        """
        Encodes texts using the GGUF model with batching.

        Args:
            texts (List[str]): The list of texts to encode.
            batch_size (int, optional): Batch size for processing. Default is 32.
            max_length (int, optional): Not used by llama-cpp's embed function, but kept for compatibility.
            use_fp16 (bool, optional): Not directly used, as GGUF quantization handles precision.

        Returns:
            torch.Tensor: A tensor of shape (n_texts, embedding_dim) moved to CPU memory.
        """
        if batch_size is None:
            batch_size = 32

        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for i in tqdm(range(0, len(texts), batch_size), desc="Encoding texts with GGUF", total=total_batches):
            batch_texts = texts[i:i + batch_size]
            # llama-cpp-python's embed method returns a list of lists of floats
            embeddings_list = self.model.embed(batch_texts)

            # Convert to a torch tensor on the CPU
            batch_tensor = torch.tensor(embeddings_list, dtype=torch.float32)
            all_embeddings.append(batch_tensor)

        result = torch.cat(all_embeddings, dim=0)
        self._free_memory()
        return result

    @property
    def embedding_dim(self) -> int:
        """Returns the embedding dimension of the model."""
        return self.model.n_embd()


def get_embedder(model_name: str, device: str = None) -> BaseEmbedder:
    """
    Factory function to get the correct embedder instance based on model name.

    Args:
        model_name (str): The name of the model.
        device (str, optional): The device to run the model on ('cpu' or 'cuda').
                                If None, will use CUDA if available, otherwise CPU.

    Returns:
        BaseEmbedder: An instance of the appropriate embedder.
        
    Raises:
        ValueError: If the model name is not supported.
    """
    model_name_lower = model_name.lower()
    if 'bge-m3' in model_name_lower:
        return BGEM3Embedder(model_name, device)
    elif 'namdp-ptit' in model_name_lower:
        return HFTransformerEmbedder(model_name, device)
    elif 'qwen/qwen3-embedding-8b-gguf' == model_name_lower:
        # Specific handling for the requested GGUF model
        # The filename is based on the user's example.
        model_filename = "Qwen3-Embedding-8B-Q4_K_M.gguf"
        return GGUFEmbedder(model_name, model_filename, device)
    elif 'gguf' in model_name_lower:
        # A more generic GGUF handler could be added here,
        # but it would require a way to specify the filename.
        raise ValueError(f"GGUF model '{model_name}' is recognized, but a specific filename is required. "
                         f"Please add specific handling for this model in get_embedder.")
    elif 'intfloat/' in model_name_lower or 'qwen' in model_name_lower or 'greennode' in model_name_lower:
        return SentenceTransformerEmbedder(model_name, device)
    else:
        # Default to SentenceTransformer for other similar models
        try:
            return SentenceTransformerEmbedder(model_name, device)
        except Exception as e:
            raise ValueError(
                f"Unsupported model_name '{model_name}' or failed to load as SentenceTransformer. Error: {e}")
