from flask import Blueprint, request, jsonify
import services.langchain_service as langchain_service  # ✅ 모듈 전체를 import하여 함수 호출 시 langchain_service.call_langchain_with_rag 사용
from services.pdf_handler import upload_pdf
from services.pdf_handler import get_uploaded_pdfs
from services.ollama_service import OllamaLLM

routes = Blueprint('routes', __name__)


@routes.route('/upload_pdf', methods=['POST'])
def upload():
    return upload_pdf()

@routes.route('/get_uploaded_pdfs', methods=['GET'])
def get_pdfs():
    return get_uploaded_pdfs()

@routes.route('/ask', methods=['POST', 'OPTIONS'])
def ask():
    # ✅ Preflight 요청(OPTIONS) 처리
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight request successful"})
        response.headers.add("Access-Control-Allow-Origin", "http://172.21.166.164:3000")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200
    
    try:
        data = request.get_json()
        question = data.get('question', '')
        rag_active = data.get('rag_active', True)  # 프론트엔드에서 전달받음

        print(f"[DEBUG] 질문: {question}, RAG 활성화 여부: {rag_active}")

        if not question:
            return jsonify({"error": "질문을 입력해주세요."}), 400

        if rag_active:
            print("[INFO] RAG 활성화됨: LangChain을 통해 Ollama 호출")
            answer = langchain_service.call_langchain_with_rag(question)  # LangChain을 통해 Ollama 호출
        else:
            print("[INFO] RAG 비활성화됨: Ollama 직접 호출")
            llm = OllamaLLM()
            answer = llm._call(question)  # 직접 클래스 호출하여 답변 생성
                
        print(f"[SUCCESS] 답변 생성 완료: {answer}")
        return jsonify({"answer_langchain": answer})

    except Exception as e:
        print(f"[ERROR] 🚨 RAG 처리 중 오류 발생: {str(e)}")
        return jsonify({"error": "서버에서 질문을 처리하는 중 오류가 발생했습니다.", "details": str(e)}), 500
    
if __name__ == "__main__":
    print("[INFO] 🚀 백엔드 서버 시작 중...")
    routes.run(debug=True, host='0.0.0.0', port=5000)