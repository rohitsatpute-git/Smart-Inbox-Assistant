FROM eclipse-temurin:25-jdk AS build
WORKDIR /src
COPY pom.xml mvnw ./
COPY .mvn .mvn
COPY src src
RUN chmod +x mvnw && ./mvnw -B -DskipTests package

FROM eclipse-temurin:25-jre
WORKDIR /app
RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*
COPY --from=build /src/target/smart-inbox-0.0.1-SNAPSHOT.jar app.jar
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=12 \
	CMD curl -fsS http://127.0.0.1:8080/actuator/health >/dev/null
ENTRYPOINT ["java", "-jar", "app.jar"]
