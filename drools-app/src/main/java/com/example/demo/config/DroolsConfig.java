package com.example.demo.config;

import org.kie.api.KieServices;
import org.kie.api.builder.KieBuilder;
import org.kie.api.builder.KieFileSystem;
import org.kie.api.builder.KieModule;
import org.kie.api.builder.Message;
import org.kie.api.runtime.KieContainer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;
import java.io.InputStream;

/**
 * Configuración del motor de reglas KIE/Drools.
 *
 * Carga el archivo DRL desde el classpath, lo compila mediante KieBuilder
 * y expone el KieContainer como Bean de Spring para su inyección en el servicio.
 */
@Configuration
public class DroolsConfig {

    private static final Logger log = LoggerFactory.getLogger(DroolsConfig.class);

    /** Ruta del archivo DRL dentro del classpath de recursos. */
    private static final String DRL_CLASSPATH = "rules/prestamos.drl";

    /**
     * Crea y expone el KieContainer como Bean de Spring.
     *
     * El proceso es:
     * 1. Obtener KieServices (singleton de la API KIE).
     * 2. Crear un KieFileSystem en memoria.
     * 3. Leer el DRL desde el classpath y escribirlo en el KieFileSystem.
     * 4. Compilar con KieBuilder y verificar errores.
     * 5. Construir y retornar el KieContainer.
     *
     * @return KieContainer con el Knowledge Base compilado y listo.
     * @throws IOException si el archivo DRL no puede leerse del classpath.
     * @throws IllegalStateException si la compilación del DRL contiene errores.
     */
    @Bean
    public KieContainer kieContainer() throws IOException {
        KieServices kieServices = KieServices.Factory.get();

        // Crear sistema de archivos en memoria para el compilador KIE
        KieFileSystem kieFileSystem = kieServices.newKieFileSystem();

        // Leer el archivo DRL desde el classpath
        try (InputStream drlInputStream = getClass().getClassLoader().getResourceAsStream(DRL_CLASSPATH)) {
            if (drlInputStream == null) {
                throw new IllegalStateException(
                        "No se encontró el archivo DRL en el classpath: " + DRL_CLASSPATH);
            }
            byte[] drlBytes = drlInputStream.readAllBytes();
            String drlContent = new String(drlBytes, java.nio.charset.StandardCharsets.UTF_8);

            // Escribir el DRL en el sistema de archivos virtual de KIE
            // La ruta debe seguir el formato: src/main/resources/<package>/<file>
            kieFileSystem.write("src/main/resources/" + DRL_CLASSPATH, drlContent);
            log.info("Archivo DRL '{}' cargado correctamente ({} bytes).", DRL_CLASSPATH, drlBytes.length);
        }

        // Compilar las reglas
        KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
        kieBuilder.buildAll();

        // Verificar errores de compilación
        if (kieBuilder.getResults().hasMessages(Message.Level.ERROR)) {
            String errores = kieBuilder.getResults().getMessages().toString();
            log.error("Errores de compilación en el DRL: {}", errores);
            throw new IllegalStateException(
                    "Error al compilar las reglas Drools. Revise el DRL. Errores: " + errores);
        }

        log.info("KieContainer construido exitosamente con las reglas de préstamos.");

        // Construir y retornar el KieContainer
        KieModule kieModule = kieBuilder.getKieModule();
        return kieServices.newKieContainer(kieModule.getReleaseId());
    }
}
