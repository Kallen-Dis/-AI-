FROM python:3.11-slim

WORKDIR /app
COPY MCP_map/requirements.txt MCP_map/requirements.txt
RUN pip install --no-cache-dir -r MCP_map/requirements.txt

COPY . .

ENV HOST=0.0.0.0
ENV PORT=5000
EXPOSE 5000

CMD ["sh", "-c", "gunicorn --chdir MCP_map -b 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 180 app:app"]
