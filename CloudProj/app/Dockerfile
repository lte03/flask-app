FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN mkdir -p /app/uploads/cvs && chmod 777 /app/uploads/cvs
RUN pip install flask
RUN pip install flask-sqlalchemy
RUN pip install flask-migrate
RUN pip install flask-login
RUN pip install Werkzeug
EXPOSE 6001
CMD [ "python" ,"app.py"]
