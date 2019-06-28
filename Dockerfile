FROM python:3-alpine

RUN apk --update add gcc musl-dev libxml2-dev libxslt-dev

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY check_stock.py .

ENTRYPOINT [ "python", "./check_stock.py"]
