# Node.js 이미지 사용
FROM node:16

# 작업 디렉터리 설정
WORKDIR /app

# package.json 파일 복사
COPY package*.json ./

# 의존성 설치
RUN npm install
RUN npm install socket.io-client

# 애플리케이션 코드 복사
COPY . .

# 애플리케이션 실행
CMD ["npm", "start"]