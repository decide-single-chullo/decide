from python:3.7-alpine

RUN apk add --no-cache git postgresql-dev gcc libc-dev
RUN apk add --no-cache gcc g++ make libffi-dev python3-dev build-base
RUN apk update && apk add --no-cache chromium curl

RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/


RUN pip install gunicorn
RUN pip install psycopg2
RUN pip install ipdb
RUN pip install ipython
RUN pip install -U pip
WORKDIR /app

RUN git clone https://github.com/decide-single-chullo/decide .
RUN git checkout develop-docker
RUN pip install -r requirements.txt

WORKDIR /app/decide

# local settings.py
ADD docker-settings.py /app/decide/local_settings.py

ARG USER_MAIL=''
ARG USER_MAIL_PASSWORD=''

RUN ./manage.py collectstatic

#CMD ["gunicorn", "-w 5", "decide.wsgi", "--timeout=500", "-b 0.0.0.0:5000"]
