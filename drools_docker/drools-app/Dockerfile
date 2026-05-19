FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jdk
COPY --from=build /app/target/drools-app-1.0.jar app.jar
ENTRYPOINT ["java","-jar","/app.jar"]