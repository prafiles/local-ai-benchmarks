# Grading sandbox for JavaScript and TypeScript tasks.
# TypeScript is pinned: --strict behaviour differs between minor releases.
FROM node:22-alpine
RUN npm install -g typescript@5.6.3 @types/node@22.20.1
WORKDIR /w
