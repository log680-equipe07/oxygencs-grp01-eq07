# docker build -t oxygen_cs-app . to build the image
# to run the image localy: docker run -it --rm oxygen_cs-app
# to run it with a pulled image: docker run -e TOKEN=b9824c123708eeeb1146 -e HOST=http://159.203.50.162 turbowarrior/oxygen_cs-app:e650d943
# Use the official Python image as the base image for the build stage
FROM python:3.12.2-alpine3.19 AS build

# Install dependencies and build Python
RUN apk add --no-cache --virtual .build-deps \
        gnupg tar xz bluez-dev bzip2-dev dpkg-dev dpkg expat-dev findutils \
        gcc gdbm-dev libc-dev libffi-dev libnsl-dev libtirpc-dev linux-headers \
        make ncurses-dev openssl-dev pax-utils readline-dev sqlite-dev tcl-dev \
        tk tk-dev util-linux-dev xz-dev zlib-dev \
    && pip install --no-cache-dir pipenv

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files
COPY Pipfile Pipfile.lock /app/

# Install dependencies
RUN pipenv install --deploy --system --ignore-pipfile && \
    # Remove unused packages
    pip uninstall -y filelock pipenv setuptools wheel

# Runtime stage
FROM python:3.12.2-alpine3.19

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files from the build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src /app/src

EXPOSE 8080

# Run the application
CMD ["python", "src/main.py"]


