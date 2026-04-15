FROM gcr.io/distroless/java21-debian12:nonroot

WORKDIR /app

ARG JAR_FILE=target/*.jar
COPY --chown=nonroot:nonroot ${JAR_FILE} /app/app.jar

EXPOSE 8080

USER nonroot:nonroot

ENTRYPOINT ["java","-XX:MaxRAMPercentage=75.0","-Djava.io.tmpdir=/tmp","-jar","/app/app.jar"]