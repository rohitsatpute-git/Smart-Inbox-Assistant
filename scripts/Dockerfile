FROM python:3.12-slim
WORKDIR /work
RUN pip install --no-cache-dir reportlab==4.4.1 pillow==11.2.1 pymupdf==1.25.5
COPY scripts/generate_testdata.py /work/scripts/generate_testdata.py
CMD ["python", "/work/scripts/generate_testdata.py"]
