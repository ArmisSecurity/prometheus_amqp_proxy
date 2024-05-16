FROM golang:bullseye

ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'APT::Install-Recommends "false";' >> /etc/apt/apt.conf.d/99_norecommends \
 && echo 'APT::AutoRemove::RecommendsImportant "false";' >> /etc/apt/apt.conf.d/99_norecommends \
 && echo 'APT::AutoRemove::SuggestsImportant "false";' >> /etc/apt/apt.conf.d/99_norecommends

# Set the working directory
WORKDIR /go/src/github.com/mishas/prometheus_amqp_proxy

# Copy the source files
COPY proxy/proxy.go proxy/
COPY proxy/rpc/*.go proxy/rpc/

# Install git, initialize Go module, install dependencies, and build binaries
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
 && cd /go/src/github.com/mishas/prometheus_amqp_proxy \
 && go mod init github.com/mishas/prometheus_amqp_proxy \
 && go get github.com/streadway/amqp@latest \
 && go mod tidy \
 && go build -o /bin/proxy ./proxy \
 && go build -o /bin/rpc ./proxy/rpc \
 && apt-get autoremove -y \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Expose the necessary port
EXPOSE 8200

# Set the entry point
ENTRYPOINT ["/bin/proxy"]