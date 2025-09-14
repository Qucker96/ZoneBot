FROM alpine:latest


RUN apk add --no-cache uv

WORKDIR /app

COPY src/ src/
COPY .env .env

RUN uv init
RUN uv add discord-py-interactions tomli-w python-dotenv pytz
CMD [ "uv", "run", "src/main.py" ]