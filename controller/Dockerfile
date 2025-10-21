FROM python:3.12-slim

RUN apt-get update

WORKDIR /app
ADD requirements.txt .
RUN pip3 install -r requirements.txt
ADD . .

CMD ["python3", "new_control_client.py"]
