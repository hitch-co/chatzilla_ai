import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from my_modules.my_logging import create_logger
runtime_logger_level = 'INFO'

class FAISSService:
    def __init__(self, embedding_model='all-MiniLM-L6-v2', top_k=50):
        self.model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.top_k = top_k

        # General FAISS index for chat history
        self.general_index = faiss.IndexFlatL2(self.embedding_dim)
        self.general_id_map = {}

        # Temporary user-specific index objects for on-demand use
        self.user_index = None
        self.user_id_map = {}

        self.logger = create_logger(
            dirname='log',
            logger_name='logger_FAISSService',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
        )

    def load_initial_messages_to_index(self, messages: list[dict]):
        """ Loads a batch of messages into the general FAISS index. """
        contents = [msg['content'] for msg in messages]
        ids = [msg['message_id'] for msg in messages]
        
        embeddings = self.model.encode(contents, convert_to_tensor=False)
        embeddings_np = np.array(embeddings).astype('float32')
        
        self.general_index.add(embeddings_np)
        for i, message_id in enumerate(ids):
            self.general_id_map[len(self.general_id_map)] = message_id

    async def add_message_to_index(self, message_metadata: dict):
        """ Adds a single message to the general FAISS index. """
        content = message_metadata['content']
        message_id = message_metadata['message_id']
        
        embedding = self.model.encode([content], convert_to_tensor=False)
        embedding_np = np.array(embedding).astype('float32')
        
        self.general_index.add(embedding_np)
        self.general_id_map[len(self.general_id_map)] = message_id

    def retrieve_similar_messages(self, query: str, index=None, id_map=None):
        """
        Retrieves top-k similar messages from a specified FAISS index.
        Defaults to general index if no index is provided.
        """
        # Use the general index and id_map by default if none provided
        index = index or self.general_index
        id_map = id_map or self.general_id_map

        query_embedding = self.model.encode([query], convert_to_tensor=False)
        query_embedding_np = np.array(query_embedding).astype('float32')
        
        distances, indices = index.search(query_embedding_np, self.top_k)
        return [id_map[idx] for idx in indices[0] if idx != -1]

    def build_and_retrieve_from_user_index(self, messages: list[dict], query: str):
        """
        Builds a temporary user-specific FAISS index and retrieves relevant messages.
        """
        # Reset the user index and id map for fresh use
        if not self.user_index:
            self.user_index = faiss.IndexFlatL2(self.embedding_dim)
        else:
            self.user_index.reset()
        
        self.user_id_map.clear()

        # Encode and add user messages
        if not messages:
            self.logger.info("No messages provided for user index. Defaulting to empty results.")
            return []

        contents = [msg['content'] for msg in messages]
        ids = [msg['message_id'] for msg in messages]
        
        if not contents:  # Ensure contents are not empty
            self.logger.warning("No valid message content found. Skipping FAISS operations.")
            return []

        embeddings = self.model.encode(contents, convert_to_tensor=False)
        embeddings_np = np.array(embeddings).astype('float32')

        # Ensure embeddings are not empty or malformed
        if embeddings_np.ndim != 2 or embeddings_np.shape[0] == 0:
            self.logger.warning("Generated embeddings are empty or malformed. Skipping FAISS operations.")
            return []

        self.user_index.add(embeddings_np)
        for i, message_id in enumerate(ids):
            self.user_id_map[i] = message_id

        # Use the unified retrieval function with the temporary user index
        return self.retrieve_similar_messages(
            query, 
            index=self.user_index, 
            id_map=self.user_id_map
        )