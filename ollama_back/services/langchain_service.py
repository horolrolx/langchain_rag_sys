from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import Qdrant
from langchain_core.language_models import LLM
from config.database import qdrant_client
from services.ollama_service import OllamaLLM

def call_langchain_with_rag(question):
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    collections = qdrant_client.get_collections().collections

    if "papers" not in [collection.name for collection in collections]:
        print("[INFO] 'papers' 컬렉션이 존재하지 않음. 새로 생성합니다.")
        qdrant_client.create_collection(
            collection_name="papers",
            vectors_config={"size": 1536, "distance": "Cosine"}
        )

    qdrant = Qdrant(
        client=qdrant_client,
        collection_name="papers",
        embeddings=embeddings
    )

    retriever = qdrant.as_retriever(search_kwargs={"k": 5})

    qa_chain = RetrievalQA.from_chain_type(
        llm=OllamaLLM(),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )

    response = qa_chain.invoke({"query": question})
    answer = response["result"]
    return answer

