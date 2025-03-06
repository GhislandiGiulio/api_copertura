FROM python:3.12

# Set the working directory inside the container
WORKDIR /app

# Update package lists and install required dependencies
RUN apt-get update && \
    apt-get install -y git ca-certificates && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Clone the GitHub repository
COPY . /app 

# Set working directory to the cloned repository
WORKDIR /app

# Ask for API credentials as an environment variable
# ARG API_USERNAME
# ARG API_PASSWORD
# ENV API_USERNAME=${API_USERNAME}
# ENV API_PASSWORD=${API_PASSWORD}

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#  starting 
CMD ["gunicorn", "--bind", "0.0.0.0:6443", "webserver_copertura:app"]
