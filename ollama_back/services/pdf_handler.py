from flask import request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_qdrant import Qdrant
from langchain_openai import OpenAIEmbeddings
from config.database import qdrant_client
from config.config import Config

UPLOAD_FOLDER = '/tmp'
# OpenAI 임베딩 설정
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

def upload_pdf():
    try:
        print("[INFO] 📂 파일 업로드 요청 수신됨.")

        # 파일이 존재하는지 확인
        if 'file' not in request.files:
            print("[ERROR] ❌ 파일이 없습니다.")
            return jsonify({"error": "파일이 없습니다."}), 400

        file = request.files['file']
        if file.filename == '':
            print("[ERROR] ❌ 파일명이 비어 있습니다.")
            return jsonify({"error": "파일명을 확인해주세요."}), 400

        # 파일 저장 경로 설정
        filename = secure_filename(file.filename)
        save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
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
                    "id": str(uuid.uuid4()),  # ID를 해시 값으로 저장
                    "vector": [0.0],  # ✅ 최소 벡터 필요 (Qdrant 제한)
                    "payload": {"filename": file.filename}
                }
            ],
        )
        print(f"[INFO] 📁 '{filename}' 파일명이 pdf_files 컬렉션에 저장됨.")

        # PDF 로딩 및 텍스트 추출
        loader = PyPDFLoader(save_path)
        documents = loader.load()
        print(f"[INFO] 📖 PDF 로드 완료: {len(documents)}개 문서")

        # 텍스트 분할
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
            
        # Qdrant 벡터 저장소에 임베딩 및 문서 저장
        qdrant = Qdrant(client=qdrant_client, collection_name="papers", embeddings=embeddings)  # 수정된 부분
        qdrant.add_documents(texts)  # 임베딩된 텍스트 저장
        print("[INFO] ✅ 문서 임베딩 저장 완료")

        # 임시 파일 삭제
        os.remove(save_path)
        print("[INFO] 🗑️ 임시 파일 삭제 완료")

        return jsonify({"message": "PDF 업로드 및 저장이 완료되었습니다."})

    except Exception as e:
        print(f"[ERROR] 🚨 업로드 및 저장 오류: {str(e)}")
        return jsonify({"error": "서버에서 처리 중 오류가 발생했습니다.", "details": str(e)}), 500


def get_uploaded_pdfs():
    try:
        print("[INFO] 📜 업로드된 PDF 목록 요청 수신됨.")
        
        # 'pdf_files' 컬렉션이 존재하는지 확인
        collections = qdrant_client.get_collections().collections
        if "pdf_files" not in [collection.name for collection in collections]:
            return jsonify({"pdfs": []})  # 컬렉션이 없으면 빈 리스트 반환

        # PDF 파일 목록 가져오기
        response = qdrant_client.scroll(
            collection_name="pdf_files",
            limit=100  # 최대 100개의 PDF 목록 반환
        )

        # PDF 파일 목록 추출
        pdf_list = [item.payload["filename"] for item in response[0]]
        print(f"[INFO] 📂 현재 업로드된 PDF 목록: {pdf_list}")
        return jsonify({"pdfs": pdf_list})

    except Exception as e:
        print(f"[ERROR] 🚨 PDF 목록 가져오기 오류: {str(e)}")
        return jsonify({"error": "서버에서 PDF 목록을 가져오는 중 오류가 발생했습니다.", "details": str(e)}), 500