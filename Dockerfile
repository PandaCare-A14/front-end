FROM eclipse-temurin:21-jdk-alpine AS builder
 
 WORKDIR /app
 COPY . .
 RUN chmod +x gradlew
 RUN ./gradlew clean bootJar
 
 FROM eclipse-temurin:21-jre-alpine AS runner
 
 ARG USER_NAME=app
 ARG USER_UID=1000
 ARG USER_GID=${USER_UID}
 
 RUN addgroup -g ${USER_GID} ${USER_NAME} \
     && adduser -h /opt/app -D -u ${USER_UID} -G ${USER_NAME} ${USER_NAME}
 
 USER ${USER_NAME}
 WORKDIR /opt/app
 COPY --from=builder --chown=${USER_UID}:${USER_GID} /app/build/libs/*.jar app.jar
 
 EXPOSE 8080
 ENTRYPOINT ["java"]
 CMD ["-jar", "app.jar"]