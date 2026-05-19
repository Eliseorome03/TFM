#!/bin/bash
set -e

# Crear estructura de directorios
mkdir -p drools-app/src/main/java/com/example/demo/controller
mkdir -p drools-app/src/main/java/com/example/demo/service
mkdir -p drools-app/src/main/java/com/example/demo/config
mkdir -p drools-app/src/main/java/com/example/demo/model
mkdir -p drools-app/src/main/resources/rules

cd drools-app

# Archivo: pom.xml
cat > pom.xml << 'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.example</groupId>
  <artifactId>drools-app</artifactId>
  <version>1.0</version>

  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
  </parent>

  <dependencies>
    <!-- API REST -->
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Drools -->
    <dependency>
      <groupId>org.drools</groupId>
      <artifactId>drools-core</artifactId>
      <version>7.74.0.Final</version>
    </dependency>

    <dependency>
      <groupId>org.drools</groupId>
      <artifactId>drools-compiler</artifactId>
      <version>7.74.0.Final</version>
    </dependency>
  </dependencies>

  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
EOF

# Archivo: src/main/java/com/example/demo/DemoApplication.java
cat > src/main/java/com/example/demo/DemoApplication.java << 'EOF'
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
EOF

# Archivo: src/main/java/com/example/demo/model/Pedido.java
cat > src/main/java/com/example/demo/model/Pedido.java << 'EOF'
package com.example.demo.model;

public class Pedido {
    private double total;
    private int descuento;

    public double getTotal() { return total; }
    public void setTotal(double total) { this.total = total; }

    public int getDescuento() { return descuento; }
    public void setDescuento(int descuento) { this.descuento = descuento; }
}
EOF

# Archivo: src/main/java/com/example/demo/config/DroolsConfig.java
cat > src/main/java/com/example/demo/config/DroolsConfig.java << 'EOF'
package com.example.demo.config;

import org.kie.api.KieServices;
import org.kie.api.runtime.KieContainer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class DroolsConfig {

    @Bean
    public KieContainer kieContainer() {
        return KieServices.Factory.get().getKieClasspathContainer();
    }
}
EOF

# Archivo: src/main/java/com/example/demo/service/DroolsService.java
cat > src/main/java/com/example/demo/service/DroolsService.java << 'EOF'
package com.example.demo.service;

import com.example.demo.model.Pedido;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.stereotype.Service;

@Service
public class DroolsService {

    private final KieContainer kieContainer;

    public DroolsService(KieContainer kieContainer) {
        this.kieContainer = kieContainer;
    }

    public Pedido ejecutar(Pedido pedido) {
        KieSession session = kieContainer.newKieSession();
        session.insert(pedido);
        session.fireAllRules();
        session.dispose();
        return pedido;
    }
}
EOF

# Archivo: src/main/java/com/example/demo/controller/RuleController.java
cat > src/main/java/com/example/demo/controller/RuleController.java << 'EOF'
package com.example.demo.controller;

import com.example.demo.model.Pedido;
import com.example.demo.service.DroolsService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/rules")
public class RuleController {

    private final DroolsService service;

    public RuleController(DroolsService service) {
        this.service = service;
    }

    @PostMapping
    public Pedido ejecutar(@RequestBody Pedido pedido) {
        return service.ejecutar(pedido);
    }
}
EOF

# Archivo: src/main/resources/rules/descuento.drl
cat > src/main/resources/rules/descuento.drl << 'EOF'
package rules;

import com.example.demo.model.Pedido;

rule "Descuento"
when
    $p : Pedido( total > 100 )
then
    $p.setDescuento(10);
end
EOF

# Archivo: Dockerfile
cat > Dockerfile << 'EOF'
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY . .
RUN mvn clean package -DskipTests

FROM openjdk:17
COPY --from=build /app/target/drools-app-1.0.jar app.jar
ENTRYPOINT ["java","-jar","/app.jar"]
EOF

echo "✅ Estructura creada en ./drools-app con los archivos solicitados."
echo "Para compilar y ejecutar:"
echo "  cd drools-app"
echo "  mvn clean package"
echo "  java -jar target/drools-app-1.0.jar"
echo "O construir la imagen Docker: docker build -t drools-app ."