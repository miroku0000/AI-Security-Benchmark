I’m locating the actual Go service entrypoint and module file so the Dockerfile targets the right build path instead of generated benchmark artifacts.

The repo doesn’t appear to contain a real Go module in the source tree, so I’m checking whether this is meant to be a generic root Dockerfile rather than something tied to an existing `go.mod`.

FROM golang:1.22

WORKDIR /app

COPY . .

RUN go mod download && CGO_ENABLED=0 GOOS=linux go build -o service .

EXPOSE 8080

CMD ["./service"]