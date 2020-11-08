FROM python:3.8
MAINTAINER MathiasSven
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
CMD [ "python3", "./bot.py" ]