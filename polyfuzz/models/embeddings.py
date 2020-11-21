import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import numpy as np
import pandas as pd
from tqdm import tqdm
from typing import List, Union
from sklearn.preprocessing import normalize
from flair.data import Sentence
from flair.embeddings import DocumentPoolEmbeddings, WordEmbeddings

from polyfuzz.models.utils import _extract_best_matches
from .base import BaseMatcher


class Embeddings(BaseMatcher):
    """
    Embed words into vectors and use cosine similarity to find
    the best matches between two lists of strings

    Arguments:
        embedding_method: list of Flair embeddings to use
        min_similarity: The minimum similarity between strings, otherwise return 0 similarity
        cosine_method: The method/package for calculating the cosine similarity.
                        Options:
                            * sparse
                            * sklearn
                            * knn

                        sparse is the fastest and most memory efficient but requires a
                        package that might be difficult to install

                        sklearn is a bit slower than sparse and requires significantly more memory as
                        the distance matrix is not sparse

                        knn uses 1-nearest neighbor to extract the most similar strings
                        it is significantly slower than both methods but requires little memory
        model_id: The name of the particular instance, used when comparing models

    Usage:

    ```python
    model = Embeddings(min_similarity=0.5)
    ```

    Or if you want a custom model to be used and it is a word embedding model,
    pass it in as a list:

    ```python
    embedding_model = WordEmbeddings('news')
    model = Embeddings([embeddings_model], min_similarity=0.5)
    ```

    As you might have guessed, you can pass along multiple word embedding models and the
    results will be averaged:

    ```python
    fasttext_embedding = WordEmbeddings('news')
    glove_embedding = WordEmbeddings('glove')
    bert_embedding = TransformerWordEmbeddings('bert-base-multilingual-cased')
    model = Embeddings([glove_embedding,
                        fasttext_embedding,
                        bert_embedding ], min_similarity=0.5)
    ```
    """
    def __init__(self,
                 embedding_method: Union[List, None] = None,
                 min_similarity: float = 0.8,
                 cosine_method: str = "sparse",
                 model_id: str = None):
        super().__init__(model_id)
        self.type = "Embeddings"

        if not embedding_method:
            self.document_embeddings = DocumentPoolEmbeddings([WordEmbeddings('news')])

        if isinstance(embedding_method, list):
            self.document_embeddings = DocumentPoolEmbeddings(embedding_method)

        else:
            self.document_embeddings = embedding_method

        self.min_similarity = min_similarity
        self.cosine_method = cosine_method

    def match(self,
              from_list: List[str],
              to_list: List[str],
              embeddings_from: np.ndarray = None,
              embeddings_to: np.ndarray = None) -> pd.DataFrame:
        """ Matches the two lists of strings to each other and returns the best mapping

        Arguments:
            from_list: The list from which you want mappings
            to_list: The list where you want to map to
            embeddings_from: Embeddings you created yourself from the `from_list`
            embeddings_to: Embeddings you created yourself from the `to_list`

        Returns:
            matches: The best matches between the lists of strings

        Usage:

        ```python
        model = Embeddings(min_similarity=0.5)
        matches = model.match(["string_one", "string_two"],
                              ["string_three", "string_four"])
        ```
        """
        if not embeddings_from:
            embeddings_from = self._embed(from_list)
        if not embeddings_to:
            embeddings_to = self._embed(to_list)
        matches = _extract_best_matches(embeddings_from, from_list,
                                        embeddings_to, to_list,
                                        self.min_similarity, self.cosine_method)
        return matches

    def _embed(self, strings: List[str]) -> np.ndarray:
        """ Create embeddings from a list of strings """
        embeddings = []
        for name in tqdm(strings):
            sentence = Sentence(name)
            self.document_embeddings.embed(sentence)
            embeddings.append(sentence.embedding.cpu().numpy())

        return np.array(normalize(embeddings), dtype="double")