package com.example.demo.controller;

import com.example.demo.model.ResultadoEvaluacion;
import com.example.demo.model.SolicitudEvaluacion;
import com.example.demo.service.DroolsService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Controlador REST que expone el endpoint de evaluación de solicitudes de préstamo.
 *
 * Endpoints aceptados:
 *   POST /evaluar          — ruta canónica definida en SYSTEM_SPEC.md.
 *   POST /api/evaluate     — ruta usada por el cliente Python (DroolsClient).
 *   Content-Type: application/json
 *   Body: {@link SolicitudEvaluacion}
 *   Response: {@link ResultadoEvaluacion}
 */
@RestController
public class RuleController {

    private static final Logger log = LoggerFactory.getLogger(RuleController.class);

    private final DroolsService droolsService;

    @Autowired
    public RuleController(DroolsService droolsService) {
        this.droolsService = droolsService;
    }

    /**
     * Evalúa una solicitud de préstamo aplicando las reglas del motor Drools.
     * Ruta canónica: POST /evaluar
     *
     * @param solicitud JSON con los datos del usuario, core bancario y externos BdE.
     * @return {@link ResultadoEvaluacion} con estado, reglas disparadas, textos legales y cálculos derivados.
     */
    @PostMapping(
            path = "/evaluar",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public ResponseEntity<ResultadoEvaluacion> evaluar(@RequestBody SolicitudEvaluacion solicitud) {
        log.info("POST /evaluar recibido. Cliente: {}",
                solicitud.getDatosCoreBancario() != null
                        ? solicitud.getDatosCoreBancario().getClienteId()
                        : "sin datos core");

        ResultadoEvaluacion resultado = droolsService.evaluar(solicitud);

        log.info("POST /evaluar respondido. Estado: {}", resultado.getEstado());
        return ResponseEntity.ok(resultado);
    }

    /**
     * Alias del endpoint de evaluación para compatibilidad con el cliente Python.
     * El cliente Python (DroolsClient) llama a http://drools-engine:8080/api/evaluate
     * tal como está configurado en DROOLS_URL del .env.
     * Ruta alternativa: POST /api/evaluate
     *
     * @param solicitud JSON con los datos del usuario, core bancario y externos BdE.
     * @return {@link ResultadoEvaluacion} con estado, reglas disparadas, textos legales y cálculos derivados.
     */
    @PostMapping(
            path = "/api/evaluate",
            consumes = MediaType.APPLICATION_JSON_VALUE,
            produces = MediaType.APPLICATION_JSON_VALUE
    )
    public ResponseEntity<ResultadoEvaluacion> evaluate(@RequestBody SolicitudEvaluacion solicitud) {
        log.info("POST /api/evaluate recibido. Cliente: {}",
                solicitud.getDatosCoreBancario() != null
                        ? solicitud.getDatosCoreBancario().getClienteId()
                        : "sin datos core");

        ResultadoEvaluacion resultado = droolsService.evaluar(solicitud);

        log.info("POST /api/evaluate respondido. Estado: {}", resultado.getEstado());
        return ResponseEntity.ok(resultado);
    }
}
