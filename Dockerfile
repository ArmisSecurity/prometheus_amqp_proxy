FROM debian:11.8-slim@sha256:d66e51af682be02ff054f86dc0c07366c0a40c6de3d8f1c731de3c633da56847

ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'APT::Install-Recommends "false";' >> /etc/apt/apt.conf.d/99_norecommends \
 && echo 'APT::AutoRemove::RecommendsImportant "false";' >> /etc/apt/apt.conf.d/99_norecommends \
 && echo 'APT::AutoRemove::SuggestsImportant "false";' >> /etc/apt/apt.conf.d/99_norecommends

# Install necessary packages
RUN apt-get update && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends \
    git \
    golang \
    ca-certificates \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /go/src/github.com/mishas/prometheus_amqp_proxy

# Copy the source files
COPY proxy/proxy.go proxy/
COPY proxy/rpc/*.go proxy/rpc/

# Initialize Go module, install dependencies, and build binaries
RUN cd /go/src/github.com/mishas/prometheus_amqp_proxy \
 && go mod init github.com/mishas/prometheus_amqp_proxy \
 && go get github.com/streadway/amqp@latest \
 && go mod tidy \
 && go build -o /bin/proxy ./proxy \
 && go build -o /bin/rpc ./proxy/rpc

# Expose the necessary port
EXPOSE 8200

# Set the entry point
ENTRYPOINT ["/bin/proxy"]