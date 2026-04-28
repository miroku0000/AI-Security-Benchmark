Creating the Dockerfile now with a fast startup-friendly Spring Boot runtime image and a generic JAR copy pattern.

The patch tool couldn't write in this environment, so I'm falling back to a direct file write to finish the Dockerfile cleanly.

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

ARG JAR_FILE=target/*.jar
COPY ${JAR_FILE} app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]