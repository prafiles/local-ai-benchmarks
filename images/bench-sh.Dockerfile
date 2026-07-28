# Grading sandbox for Bash, Git and SSH tasks.
# ssh is needed for `ssh -G` config expansion, git for the fixture repositories.
FROM alpine:3.20
RUN apk add --no-cache git openssh-client gzip coreutils findutils grep sed
WORKDIR /w
