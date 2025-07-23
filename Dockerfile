FROM --platform=linux/amd64 python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install pymupdf
ENTRYPOINT ["python", "extractor.py"]
