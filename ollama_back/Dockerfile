# CUDA 런타임 이미지 (Ubuntu 20.04 기반)
FROM nvidia/cuda:11.8.0-runtime-ubuntu20.04

# 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    python3 python3-pip python-is-python3 git && \
    rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r /app/requirements.txt

# 애플리케이션 코드 복사
COPY . /app

# 포트 설정
EXPOSE 5000

CMD ["python3", "-u", "app.py"]