FROM python:3.10

RUN mkdir -p /usr/bot
WORKDIR /usr/bot

COPY . .

RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py" ]