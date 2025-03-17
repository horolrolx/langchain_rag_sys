import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isTTSActive, setIsTTSActive] = useState(false);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState('');
  const [isRAGActive, setIsRAGActive] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [selectedFileName, setSelectedFileName] = useState(''); // 📌 추가: 선택한 파일명 표시
  const [uploadedPDFs, setUploadedPDFs] = useState([]); // 📌 추가된 부분
  const chatBoxRef = useRef(null);
  const inputRef = useRef(null);
  const [speakingIndex, setSpeakingIndex] = useState(null); // 현재 음성 읽는 메시지 인덱스 상태
  const [voices, setVoices] = useState([]);
  const [activeSpeech, setActiveSpeech] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  useEffect(() => {
    fetchUploadedPDFs(); // 📌 추가: 페이지 로드 시 PDF 목록 불러오기
    const loadVoices = () => {
      const availableVoices = window.speechSynthesis.getVoices();
      if (availableVoices.length) {
        setVoices(availableVoices);
      } else {
        setTimeout(loadVoices, 100);
      }
    };
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
    if (inputRef.current) inputRef.current.focus();
  }, [chatHistory]);

  const handleQuestionChange = (e) => {
    setQuestion(e.target.value);
    setError('');
  };

  // ✅ 1. 함수 추가 (엔터 키 감지)
const handleKeyPress = (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault(); // 기본 개행(줄바꿈) 방지
    handleAsk(e); // 전송 함수 호출
  }
};

  // 📌 추가: 업로드된 PDF 목록을 가져오는 함수
  const fetchUploadedPDFs = async () => {
    try {
      const response = await axios.get('http://172.21.166.164:5000/get_uploaded_pdfs');
      console.log("[INFO] 📜 서버에서 가져온 PDF 목록:", response.data.pdfs); // 디버깅 로그 추가
      setUploadedPDFs(response.data.pdfs);
    } catch (error) {
      console.error('[ERROR] ❌ PDF 목록을 불러오는 중 오류 발생:', error);
    }
  };

  const handleCopy = (text, index) => {
    if (!text) return; // 빈 텍스트 방지
  
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index); // ✅ 해당 인덱스 버튼을 "복사됨"으로 변경
      setTimeout(() => setCopiedIndex(null), 2000); // ✅ 2초 후 다시 "복사"로 변경
    }).catch((err) => console.error("[ERROR] 복사 실패:", err));
  };

  const handleSpeechPlay = (text, index) => {
    if (activeSpeech || speakingIndex !== null) {
      return; // ✅ 이미 음성을 읽고 있으면 클릭 불가능하게 처리
    }
    
    const speech = new SpeechSynthesisUtterance(text);
    speech.voice = voices.find((voice) => voice.lang === 'ko-KR') || voices[0];
  
    speech.onstart = () => setSpeakingIndex(index); // ✅ 해당 인덱스의 버튼을 "음성 읽는 중..."으로 변경
    speech.onend = () => {
      setSpeakingIndex(null); // ✅ 음성이 끝나면 원래 상태로 복귀
      setActiveSpeech(null);
    };
  
    setActiveSpeech(speech);
    window.speechSynthesis.speak(speech);
  };
  const handleSpeechStop = () => {
    if (activeSpeech) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null); // ✅ 정지 버튼을 누르면 버튼 상태 초기화
      setActiveSpeech(null);
    }
  };
  // 자동 음성 읽기 기능 활성화/비활성화
  const handleTTS = () => {
    if (isTTSActive) {
      handleSpeechStop(); // 자동 음성 읽기 끄기가 활성화되면 즉시 정지
    }
    setIsTTSActive(!isTTSActive);
  };

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) {
      setError('질문을 입력해주세요.');
      if (inputRef.current) inputRef.current.focus();
      return;
    }

    setLoading(true);
    setError('');

    setChatHistory((prevHistory) => [...prevHistory, { user: question }]);

    try {
      // RAG 상태에 따라 다른 엔드포인트로 요청
      const url = isRAGActive 
        ? 'http://172.21.166.164:5000/ask' // RAG가 활성화된 경우
        : 'http://172.21.166.164:5000/ask'; // RAG가 비활성화된 경우

      // RAG 활성화 상태에 따라 질문을 보내는 형식 변경
      const response = await axios.post(url, { question: question }, {
        headers: { 'Content-Type': 'application/json' },
        withCredentials: true, // CORS 문제 해결을 위한 설정
      });

      // RAG 응답 처리
      const answerRAG = response.data.answer_crew;
      const answerLangchain = response.data.answer_langchain;
      const finalAnswer = isRAGActive ? answerRAG : answerLangchain;

      setChatHistory((prevHistory) => [...prevHistory, { bot: answerLangchain }]);
      setQuestion('');

      if (isTTSActive && voices.length > 0) {
        const speech = new SpeechSynthesisUtterance(finalAnswer);
        const language = 'ko-KR';
        const selectedVoice = voices.find((voice) => voice.lang === language);
        speech.voice = selectedVoice || voices[0]; 
        window.speechSynthesis.speak(speech);
      }
    } catch (error) {
      console.error(error);
      setError('질문 전송 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError('이 브라우저는 음성 인식을 지원하지 않습니다.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setQuestion(transcript);
      if (inputRef.current) inputRef.current.focus();
    };

    recognition.onerror = (event) => {
      setError('음성 인식 오류가 발생했습니다. 마이크를 확인해 주세요.');
      console.error(event.error);
    };

    recognition.start();
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setSelectedFileName(file ? file.name : ''); // 📌 추가: 파일명 표시
  };

  const handlePDFUpload = async () => {
    if (!selectedFile) {
      setUploadStatus('파일을 선택해주세요.');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setUploadStatus('📤 PDF 업로드 중...');
      await axios.post('http://172.21.166.164:5000/upload_pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadStatus('✅ 업로드 완료!');
      setSelectedFile(null);
      setSelectedFileName('');
      fetchUploadedPDFs(); // 📌 업로드 후 목록 갱신
    } catch (error) {
      console.error('[ERROR] ❌ PDF 업로드 중 오류 발생:', error);
      setUploadStatus('업로드 실패! 다시 시도해주세요.');
    }
  };

  return (
    <>
<h1 className="app-header">Ollama 챗봇</h1>
<div className="app-container">
  {/* ✅ 기존 버튼 스타일을 개선하여 토글 UI 적용 */}
  <div className="toggle-container">
    <label className="switch">
      <input type="checkbox" checked={isRAGActive} onChange={() => setIsRAGActive(!isRAGActive)} />
      <span className="slider round"></span>
    </label>
    <span className="toggle-label">{isRAGActive ? '📘 RAG ' : '📘 RAG '}</span>
  </div>

  <div className="chat-container">
    <div className="chat-box" ref={chatBoxRef}>
      <div className="chat-history">
        {chatHistory.length === 0 ? (
          <div className="no-chat-message">대화 내용이 없습니다.</div>
        ) : (
          chatHistory.map((chat, index) => (
            <div key={index} className="chat-message">
              {chat.user && (
                <div className="user-message">
                  <span contenteditable="false" className="user-icon">👤</span> {chat.user}
                </div>
              )}
              {chat.bot && (
                <div className="bot-message">
                  <div className="bot-message-text">
                    <span contenteditable="false" className="bot-icon">🤖</span>
                    {chat.bot}
                  </div>
                  <div className="speech-controls">
                    {/* ✅ 복사 버튼 추가 */}
                    <button 
                      className="copy-button" 
                      onClick={() => handleCopy(chat.bot, index)}
                    >
                      {copiedIndex === index ? "✅ 복사됨" : "📋 복사"}
                    </button>
                    <button 
                      className="speech-play-button" 
                      onClick={() => handleSpeechPlay(chat.bot, index)}
                      disabled={speakingIndex !== null} // ✅ 음성 읽는 중이면 클릭 불가능
                    >
                      {speakingIndex === index ? "🔊 음성 읽는 중..." : "🔊 음성 읽기"}
                    </button>
                    <button className="speech-stop-button" onClick={handleSpeechStop}>
                      ⏹️ 음성 정지
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  </div>
</div>

{/* ✅ 하단 고정 컨테이너 */}
<div className="chat-footer">
  <form className="chat-input-form" onSubmit={handleAsk}>
    <textarea
      ref={inputRef}
      value={question}
      onChange={handleQuestionChange}
      onKeyDown={handleKeyPress}
      placeholder="궁금한 점을 입력해 주세요..."
      rows="4"
      className="input-box"
      disabled={loading}
    />
    <button type="submit" className="send-button" disabled={loading}>
      {loading ? '전송 중...' : '전송'}
    </button>
  </form>
  {loading && <div className="loading-message">답변을 생성 중입니다...</div>}
  {notification && <div className="notification-message">{notification}</div>}
  {error && <div className="error-message">{error}</div>}
  <button className="voice-button" onClick={handleSpeechRecognition}>
    🎤 음성 인식
  </button>
  <button className="tts-toggle-button" onClick={handleTTS}>
    {isTTSActive ? '🔊 자동 음성 읽기 끄기' : '🔊 자동 음성 읽기 켜기'}
  </button>
</div>

<div className="sidebar">
  <div className="sidebar-content">
    {/* 📌 PDF 업로드 섹션 */}
    <div className="sidebar-upload-section">
      <label htmlFor="sidebar-pdf-upload" className="sidebar-upload-button">
        📁 파일 선택
      </label>
      <input id="sidebar-pdf-upload" type="file" accept=".pdf" onChange={handleFileChange} style={{ display: 'none' }} />
      
      {/* 선택된 파일명 표시 */}
      <span className="selected-file-name">
        {selectedFileName || "선택된 파일 없음"}
      </span>

      {/* 업로드 버튼 */}
      <button className="sidebar-upload-button" onClick={handlePDFUpload} disabled={!selectedFile}>
        📤 업로드
      </button>
      {/* 업로드 상태 표시하고 목록 재갱신 */}
      <div className="upload-status">{uploadStatus}</div>
    </div>

    <div className="sidebar-uploaded-pdfs">
      <h3>📚 업로드된 PDF 목록</h3>
      {uploadedPDFs.length > 0 ? (
        <ul>
          {uploadedPDFs.map((pdf, index) => (
            <li key={index}> {pdf}</li>
          ))}
        </ul>
      ) : (
        <div className="no-pdf-message">
          <span className="no-pdf-icon">❌</span>
          <span className="no-pdf-text">업로드된 파일이 없습니다.</span>
        </div>
      )}
    </div>
  </div>
</div>

    </>
  );
}

export default App;
