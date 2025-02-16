import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from my_modules.my_logging import create_logger
runtime_logger_level = 'INFO'

class FAISSService:
    def __init__(self, embedding_model='all-MiniLM-L6-v2', top_k=50):

        self.logger = create_logger(
            dirname='log',
            logger_name='logger_FAISSService',
            debug_level=runtime_logger_level,
            mode='w',
            stream_logs=True,
            encoding='UTF-8'
        )

        # General FAISS index for chat history
        self.transformer_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.transformer_model.get_sentence_embedding_dimension()
        self.session_index = faiss.IndexFlatL2(self.embedding_dim)
        self.top_k = top_k
        self.session_msg_id_map = {}

        self.logger.info(f"Initialized FAISSService with embedding_model: {embedding_model} and top_k: {top_k}")

    def load_initial_msgs_to_session_index(self, messages: list[dict]):
        """ Loads a batch of messages into the general FAISS index. """
        contents = [f"{msg['user_login']} ({msg['timestamp']}): {msg['content']}" for msg in messages]
        ids = [msg['message_id'] for msg in messages]
        
        embeddings = self.transformer_model.encode(contents, convert_to_tensor=False)
        embeddings_np = np.array(embeddings).astype('float32')
        
        self.session_index.add(embeddings_np)
        for i, message_id in enumerate(ids):
            self.session_msg_id_map[len(self.session_msg_id_map)] = message_id

    async def add_message_to_index(self, message_metadata: dict):
        """ Adds a single message to the general FAISS index. """
        content = message_metadata['content']
        message_id = message_metadata['message_id']
        
        embedding = self.transformer_model.encode([content], convert_to_tensor=False)
        embedding_np = np.array(embedding).astype('float32')
        
        self.session_index.add(embedding_np)
        self.session_msg_id_map[len(self.session_msg_id_map)] = message_id

        self.logger.debug(f"...Added message to FAISS index: {message_id}")
        self.logger.debug(f"...Current index size: {self.session_index.ntotal}")

    def _retrieve_similar_messages(self, query: str, index=None, id_map=None):
        """
        Retrieves top-k similar messages from a specified FAISS index.
        Defaults to general index if no index is provided.
        """
        # Use the general index and id_map by default if none provided
        index = index or self.session_index
        id_map = id_map or self.session_msg_id_map

        query_embedding = self.transformer_model.encode([query], convert_to_tensor=False)
        query_embedding_np = np.array(query_embedding).astype('float32')
        
        distances, indices = index.search(query_embedding_np, self.top_k)

        return [id_map[idx] for idx in indices[0] if idx != -1]

    def build_and_retrieve_from_faiss_index(
            self, 
            query: str,
            messages: list[dict] = None,
            messages_to_forget: list[dict] = None
            ):
        """
        Builds a temporary user-specific FAISS index and retrieves relevant messages.
        """

        def extract_forget_phrases(
                msgs: list[dict],
                filter_criteria = "!forget",
                starts_with = True
                ) -> list[str]:
            """
            Given a list of messages that each contain '!forget ...',
            return a list of the actual phrases to forget.
            e.g.: "!forget my Christmas present" -> "my Christmas present"
            """
            phrases = []
            for m in msgs:
                content = m["content"] or ""
                if starts_with and content.startswith(filter_criteria):
                    content = content[len(filter_criteria):]
                phrase_to_forget = content.strip()
                if phrase_to_forget:
                    phrases.append(phrase_to_forget)
            return phrases
        
        # If no messages, bail out
        if not messages:
            self.logger.info("No messages provided for local index; using session index instead.")
            return self._retrieve_similar_messages(query)

        else:
            local_index = faiss.IndexFlatL2(self.embedding_dim)
            local_msg_id_map = {}

            # Get messages and add to the user index
            contents = [msg['content'] for msg in messages]
            ids = [msg['message_id'] for msg in messages]
            if not contents or not ids:
                self.logger.warning("No valid message content found. Skipping FAISS operations.")
                return []
            else:
                embeddings = self.transformer_model.encode(contents, convert_to_tensor=False)
                embeddings_np = np.array(embeddings).astype('float32')

            if embeddings_np.ndim != 2 or embeddings_np.shape[0] == 0:
                self.logger.warning("Generated embeddings are empty or malformed. Skipping FAISS operations.")
                return []
            else:
                local_index.add(embeddings_np)
                for i, message_id in enumerate(ids):
                    local_msg_id_map[i] = message_id

        # ------------- Build a list of 'similar' message_ids ------------
        similar_message_ids = self._retrieve_similar_messages(
            query,
            index=local_index,
            id_map=local_msg_id_map
        )

        # ------------- Build the set of 'forgotten' message_ids ------------
        forgotten_message_ids = set()
        if messages_to_forget is None:
            messages_to_forget = []
        else:
            phrase_list = extract_forget_phrases(
                msgs=messages_to_forget,
                filter_criteria="!forget",
                starts_with=True
                )

            # For each phrase, do a retrieval
            for phrase in phrase_list:
                phrase_ids = self._retrieve_similar_messages(
                    query=phrase,
                    index=local_index,
                    id_map=local_msg_id_map
                )
                forgotten_message_ids.update(phrase_ids)
        
        # ------------- Exclude the forgotten IDs -------------
        final_filtered_messages = [mid for mid in similar_message_ids if mid not in forgotten_message_ids]

        return final_filtered_messages