from qdrant_client import QdrantClient
from config.config import Config

qdrant_client = QdrantClient(url=Config.QDRANT_URL)