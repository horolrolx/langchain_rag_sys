# ollama_chatbot
1. ollama_back > app.py에서 IP인 172.21.166.164 이 부분 지우고 본인 IP or localhost로 변경

2. app.py 22번째 줄 본인 OPEN API KEY로 설정할 것

3. ollama_front > ollama-web > src > App.js에서도 1번과 똑같이 해줄 것

4. 마지막으로 프로젝트 경로에서 터미널에 docker-compose up -d --build

5. 본인아이피:3000 으로 접속

-----
단, 로컬 컴퓨터. 자신의 컴퓨터가 올라마가 설치가 되어있어야함.

Model : exaone3.5:latest

모델 변경 가능
