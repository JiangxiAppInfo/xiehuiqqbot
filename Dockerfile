FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN python -c "import subprocess, tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.check_call(['python', '-m', 'pip', 'install', '--no-cache-dir', *deps])"

COPY bot.py README.md ./
COPY plugins/ ./plugins/
COPY config/ ./config/

EXPOSE 9090

CMD ["python", "bot.py"]
