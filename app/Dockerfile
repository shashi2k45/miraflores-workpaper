# MiraFlores workpaper — one-command container build.
# Build context must be the PROJECT folder (../), because the app reads the
# packet JSON from its parent directory:
#
#   cd ~/workspace/miraflores-case-study
#   docker build -f app/Dockerfile -t miraflores-workpaper .
#   docker run -p 8765:8765 miraflores-workpaper
#   -> http://localhost:8765/
#
FROM python:3.12-slim
WORKDIR /srv/case-study
COPY okafor_lindqvist_2025_packet.json ./
COPY app/requirements.txt app/
RUN pip install --no-cache-dir -r app/requirements.txt
COPY app/main.py app/state_store.py app/
COPY app/static app/static
# Review state (notes/sign-offs/...) persists in the container filesystem.
# For a hosted deploy, mount a volume at /srv/case-study/app or set
# WORKPAPER_STATE_DB to a path on persistent storage.
WORKDIR /srv/case-study/app
EXPOSE 8765
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8765"]
