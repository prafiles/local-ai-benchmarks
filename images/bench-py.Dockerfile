# Grading sandbox for Python, Django, SQL and GitHub-Actions YAML tasks.
# Run with --network none: nothing here should reach the internet.
FROM python:3.12-slim-trixie
RUN pip install --no-cache-dir Django==5.1.4 PyYAML==6.0.2 sqlparse==0.5.5
WORKDIR /w
