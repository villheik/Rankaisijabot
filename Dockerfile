FROM python:3.9-slim

ARG bot_token_arg

# Set pip to have cleaner logs and no saved cache
ENV PIP_NO_CACHE_DIR=false \
    PIPENV_HIDE_EMOJIS=1 \
    PIPENV_IGNORE_VIRTUALENVS=1 \
    PIPENV_NOSPIN=1 \
    BOT_TOKEN=$bot_token_arg

RUN apt-get update && apt-get -y dist-upgrade

RUN apt-get install gcc g++

RUN pip install --upgrade pip

# Create the working directory
WORKDIR /bot

# Install project dependencies
COPY requirements* ./
RUN pip3 install -r requirements.txt

# Copy the source code in last to optimize rebuilding the image
COPY . .

ENTRYPOINT ["python3"]
CMD ["-m", "bot"]