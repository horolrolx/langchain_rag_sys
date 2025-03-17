import os
from flask import Flask, request, jsonify
import requests
import sys
from flask_cors import CORS
import torch
from flask_pymongo import PyMongo
from langchain_openai import OpenAIEmbeddings  # langchain-openai 패키지
from langchain_community.vectorstores import Qdrant  # langchain-community 패키지
from langchain_core.language_models import LLM  # langchain-core 패키지
from langchain_community.document_loaders import PyPDFLoader  # langchain-community 패키지
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
from dotenv import load_dotenv  # 환경 변수 파일을 불러오는 패키지

# .env 파일에서 환경 변수를 로드
load_dotenv()

class Config:
    # 업로드 폴더 경로
    UPLOAD_FOLDER = "/tmp"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # OpenAI API 키 (환경변수에서 불러오기 권장)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # .env에서 불러오기
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API Key가 환경변수에 설정되지 않았습니다.")
    
    # Qdrant 설정
    QDRANT_URL = os.getenv("QDRANT_URL", "http://host.docker.internal:6333")  # 기본값 설정
    
    # Flask 설정
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://172.21.166.164:3000").split(',')

# .env 파일에서 환경 변수 설정
# 예시 .env 파일 내용
# OPENAI_API_KEY=your-openai-api-key
# QDRANT_URL=http://your-qdrant-url
# CORS_ORIGINS=http://your-client-origin