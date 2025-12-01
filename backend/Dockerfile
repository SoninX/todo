FROM python:3.9-slim

WORKDIR /code

# 1. Install dependencies first (Cached layer)
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 2. Copy the entire backend project into the container
COPY . /code

# 3. Run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]