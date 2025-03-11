from flask import Flask, request, jsonify
import requests
import sys
from flask_cors import CORS
import torch
from flask_pymongo import PyMongo
from langchain.chains import RetrievalQA
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Qdrant
from langchain.llms.base import LLM
from qdrant_client import QdrantClient
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
import os

uploaded_pdfs = []  # 📌 업로드된 PDF 목록 저장
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# OpenAI API 키 설정 (본인의 API 키를 넣어주세요)
os.environ["OPENAI_API_KEY"] = "openai-api-key"

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["http://172.21.166.164:3000"])
qdrant_client = QdrantClient(url="http://172.21.166.164:6333")
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
sys.stdout.reconfigure(encoding='utf-8')

SYSTEM_PROMPT = (
    "당신은 질문-답변 AI 어시스턴트입니다. 주어진 문맥(context)에서 질문에 대해 답변하세요. "
    "정보가 없으면 '주어진 정보에서 질문에 대한 정보를 찾을 수 없습니다'라고 답하세요. "
    "한글로 답변하되, 기술 용어는 그대로 사용합니다."
)

class OllamaLLM(LLM):
    @property
    def _llm_type(self) -> str:
        return "ollama"

    def _call(self, prompt: str, stop=None) -> str:
        url = "http://host.docker.internal:11434/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "model": "exaone3.5:latest"
        }

        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()

        result = response.json()
        return result.get('choices', [{}])[0].get('message', {}).get('content', '정보를 찾을 수 없습니다.')


def call_langchain_with_rag(question):
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    qdrant_client = QdrantClient(url="http://172.21.166.164:6333")

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
        embedding_function=embeddings.embed_query
    )

    retriever = qdrant.as_retriever(search_kwargs={"k": 5})

    qa_chain = RetrievalQA.from_chain_type(
        llm=OllamaLLM(),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True  # 결과에 source_documents 포함
    )

    response = qa_chain({"query": question})  # invoke() 대신 이렇게 변경
    answer = response["result"]  # 'result' 키에서 답변만 추출
    return answer

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    try:
        print("[INFO] 📂 파일 업로드 요청 수신됨.")

        if 'file' not in request.files:
            print("[ERROR] ❌ 파일이 없습니다.")
            return jsonify({"error": "파일이 없습니다."}), 400

        file = request.files['file']
        if file.filename == '':
            print("[ERROR] ❌ 파일명이 비어 있습니다.")
            return jsonify({"error": "파일명을 확인해주세요."}), 400

        filename = secure_filename(file.filename)
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        print(f"[INFO] ✅ 파일 저장 완료: {save_path}")

        # 📌 'pdf_files' 컬렉션이 없으면 생성 (파일명만 저장)
        collections = qdrant_client.get_collections().collections
        if "pdf_files" not in [collection.name for collection in collections]:
            print("[INFO] 'pdf_files' 컬렉션이 존재하지 않음. 새로 생성합니다.")
            qdrant_client.create_collection(
                collection_name="pdf_files",
                vectors_config={"size": 1, "distance": "Cosine"}  # ✅ 파일명을 저장하기 위해 최소 벡터 설정 필요
            )

        # 📌 'pdf_files' 컬렉션에 파일명 저장
        qdrant_client.upsert(
            collection_name="pdf_files",
            points=[
                {
                    "id": hash(filename),  # ID를 해시 값으로 저장
                    "vector": [0.0],  # ✅ 최소 벡터 필요 (Qdrant 제한)
                    "payload": {"filename": file.filename}
                }
            ]
        )
        print(f"[INFO] 📁 '{filename}' 파일명이 pdf_files 컬렉션에 저장됨.")

        # PDF 임베딩 및 "papers" 컬렉션 저장
        loader = PyPDFLoader(save_path)
        documents = loader.load()
        print(f"[INFO] 📖 PDF 로드 완료: {len(documents)}개 문서")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        print(f"[INFO] ✂️ 텍스트 분할 완료: {len(texts)}개 청크")

        # 📌 'papers' 컬렉션이 없으면 생성 (PDF 내용 저장용)
        collections = qdrant_client.get_collections().collections
        if "papers" not in [collection.name for collection in collections]:
            print("[INFO] 'papers' 컬렉션이 존재하지 않음. 새로 생성합니다.")
            qdrant_client.create_collection(
                collection_name="papers",
                vectors_config={"size": 1536, "distance": "Cosine"}  # ✅ PDF 임베딩 저장용
            )

        # PDF 내용 임베딩 후 저장
        qdrant = Qdrant(client=qdrant_client, collection_name="papers", embedding_function=embeddings.embed_query)
        qdrant.add_documents(texts)
        print("[INFO] ✅ 문서 임베딩 저장 완료")

        os.remove(save_path)
        print("[INFO] 🗑️ 임시 파일 삭제 완료")

        return jsonify({"message": "PDF 업로드 및 저장이 완료되었습니다."})

    except Exception as e:
        print(f"[ERROR] 🚨 업로드 및 저장 오류: {str(e)}")
        return jsonify({"error": "서버에서 처리 중 오류가 발생했습니다.", "details": str(e)}), 500

# 📌 추가: 'pdf_files' 컬렉션에서 업로드된 PDF 목록 반환
@app.route('/get_uploaded_pdfs', methods=['GET'])
def get_uploaded_pdfs():
    qdrant_client = QdrantClient(url="http://172.21.166.164:6333")
    try:
        print("[INFO] 📜 업로드된 PDF 목록 요청 수신됨.")
        collections = qdrant_client.get_collections().collections
        if "pdf_files" not in [collection.name for collection in collections]:
            return jsonify({"pdfs": []})  # 컬렉션이 없으면 빈 리스트 반환

        response = qdrant_client.scroll(
            collection_name="pdf_files",
            limit=100
        )

        pdf_list = [item.payload["filename"] for item in response[0]]
        print(f"[INFO] 📂 현재 업로드된 PDF 목록: {pdf_list}")
        return jsonify({"pdfs": pdf_list})

    except Exception as e:
        print(f"[ERROR] 🚨 PDF 목록 가져오기 오류: {str(e)}")
        return jsonify({"error": "서버에서 PDF 목록을 가져오는 중 오류가 발생했습니다.", "details": str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '')
    rag_active = data.get('rag_active', True)  # 프론트엔드로부터 전달받음

    print(f"[DEBUG] 질문: {question}, RAG 활성화 여부: {rag_active}")

    if not question:
        return jsonify({"error": "질문을 입력해주세요."}), 400

    if rag_active:
        print("[INFO] RAG 활성화됨: LangChain을 통해 Ollama 호출")
        answer = call_langchain_with_rag(question)
    else:
        print("[INFO] RAG 비활성화됨: Ollama 직접 호출")
        llm = OllamaLLM()
        answer = llm._call(question)  # 직접 클래스 호출하여 답변 생성
    print(f"[SUCCESS] 답변 생성 완료: {answer}")
    return jsonify({"answer_langchain": answer})

if __name__ == "__main__":
    print("[INFO] 🚀 백엔드 서버 시작 중...")
    app.run(debug=True, host='0.0.0.0', port=5000)