FROM ubuntu:22.04
RUN apt update
RUN apt install python3.10 -y
RUN apt install python3-pip -y
RUN pip3.10 install flask
RUN pip3.10 install db-sqlite3
WORKDIR /app
COPY app.py .
RUN touch database.db
CMD [ "python3.10", "app.py" ]