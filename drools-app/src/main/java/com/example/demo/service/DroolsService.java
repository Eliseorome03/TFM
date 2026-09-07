package com.example.demo.service;

import com.example.demo.model.CalculosDerivados;
import com.example.demo.model.DatosCoreBancario;
import com.example.demo.model.DatosExternosBde;
import com.example.demo.model.DatosUsuario;
import com.example.demo.model.ResultadoEvaluacion;
import com.example.demo.model.SolicitudEvaluacion;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/**
 * Servicio principal del motor de reglas Drools.
 *
 * Responsabilidades:
 * 1. Calcular los {@link CalculosDerivados} a partir de los datos de entrada.
 * 2. Crear una KieSession stateless por petición (thread-safe).
 * 3. Insertar todos los facts en la sesión.
 * 4. Disparar las reglas (fireAllRules).
 * 5. Devolver el {@link ResultadoEvaluacion} enriquecido.
 */
@Service
public class DroolsService {

    private static final Logger log = LoggerFactory.getLogger(DroolsService.class);

    private final KieContainer kieContainer;

    @Autowired
    public DroolsService(KieContainer kieContainer) {
        this.kieContainer = kieContainer;
    }

    /**
     * Evalúa una solicitud de préstamo aplicando el catálogo de reglas Drools.
     *
     * @param solicitud DTO con los datos del usuario, core bancario y externos BdE.
     * @return {@link ResultadoEvaluacion} con el estado, reglas disparadas, textos legales y cálculos.
     */
    public ResultadoEvaluacion evaluar(SolicitudEvaluacion solicitud) {
        log.info("Iniciando evaluación Drools para cliente: {}",
                solicitud.getDatosCoreBancario() != null
                        ? solicitud.getDatosCoreBancario().getClienteId()
                        : "desconocido");

        DatosUsuario datosUsuario = solicitud.getDatosUsuario();
        DatosCoreBancario datosCore = solicitud.getDatosCoreBancario();
        DatosExternosBde datosBde = solicitud.getDatosExternosBde();

        // =====================================================================
        // Paso 1: Calcular los CalculosDerivados
        // Si alguna variable necesaria es null, el campo derivado resulta null
        // para evitar NullPointerException y mantener la evaluación null-safe en DRL.
        // =====================================================================
        CalculosDerivados calculosDerivados = calcularDerivados(datosUsuario, datosCore, datosBde);
        log.debug("Cálculos derivados obtenidos: {}", calculosDerivados);

        // =====================================================================
        // Paso 2: Crear KieSession stateless por petición
        // =====================================================================
        KieSession kieSession = kieContainer.newKieSession();

        // =====================================================================
        // Paso 3: Crear el ResultadoEvaluacion inicial (estado="EN_PROCESO")
        // =====================================================================
        ResultadoEvaluacion resultado = new ResultadoEvaluacion();
        // El estado "EN_PROCESO" ya está inicializado en el constructor del modelo.

        try {
            // =====================================================================
            // Paso 4: Insertar todos los facts en la sesión
            // =====================================================================
            kieSession.insert(datosUsuario);
            kieSession.insert(datosCore);
            kieSession.insert(datosBde);
            kieSession.insert(calculosDerivados);
            kieSession.insert(resultado);

            log.debug("Facts insertados en la KieSession. Disparando reglas...");

            // =====================================================================
            // Paso 5: Ejecutar las reglas
            // =====================================================================
            int reglasFired = kieSession.fireAllRules();
            log.info("Reglas disparadas: {}. Estado final: {}", reglasFired, resultado.getEstado());

        } finally {
            // =====================================================================
            // Paso 6: Cerrar la sesión siempre (incluso si hay excepción)
            // =====================================================================
            kieSession.dispose();
        }

        // =====================================================================
        // Paso 7: Asociar los CalculosDerivados al resultado y devolverlo
        // =====================================================================
        resultado.setCalculosDerivados(calculosDerivados);

        log.info("Evaluación completada. Estado: {}. Reglas disparadas: {}",
                resultado.getEstado(), resultado.getReglasDisparadas());

        return resultado;
    }

    /**
     * Calcula los campos derivados a partir de los datos de entrada.
     * Cualquier campo cuya fórmula requiera un valor null devuelve null,
     * evitando {@link NullPointerException} y permitiendo que las reglas DRL
     * evalúen los nulos correctamente.
     *
     * Fórmulas aplicadas:
     * <pre>
     *   cuotaEstimada         = cantidadSolicitada / plazoMeses
     *   ratioEndeudamiento    = (cuotaEstimada + gastosFijosMensuales + deudaInternaBancoMensual + deudaCirbeMensual) / ingresosNetosMensuales
     *   remanenteSubsistencia = ingresosNetosMensuales - (cuotaEstimada + gastosFijosMensuales + deudaInternaBancoMensual + deudaCirbeMensual)
     *   edadAlVencimiento     = edad + (plazoMeses / 12)
     * </pre>
     *
     * @param datosUsuario datos del usuario.
     * @param datosCore    datos del core bancario.
     * @param datosBde     datos externos del BdE.
     * @return {@link CalculosDerivados} con los valores calculados (o null si no se pueden calcular).
     */
    private CalculosDerivados calcularDerivados(DatosUsuario datosUsuario,
                                                DatosCoreBancario datosCore,
                                                DatosExternosBde datosBde) {
        CalculosDerivados calc = new CalculosDerivados();

        // --- cuotaEstimada = cantidadSolicitada / plazoMeses ---
        Double cuotaEstimada = null;
        if (datosUsuario.getCantidadSolicitada() != null
                && datosUsuario.getPlazoMeses() != null
                && datosUsuario.getPlazoMeses() != 0) {
            cuotaEstimada = datosUsuario.getCantidadSolicitada()
                    / datosUsuario.getPlazoMeses().doubleValue();
        }
        calc.setCuotaEstimada(cuotaEstimada);

        // --- Variables intermedias (con null-checks) ---
        Double gastosFijos = datosUsuario.getGastosFijosMensuales();
        Double deudaInternaBanco = datosCore.getDeudaInternaBancoMensual();
        Double deudaCirbeMensual = (datosBde != null) ? datosBde.getDeudaCirbeMensual() : null;
        Double ingresos = datosCore.getIngresosNetosMensuales();

        // --- Total de compromisos mensuales (para ratio y remanente) ---
        // Sólo calculable si todos los componentes son no-null
        Double totalCompromisos = null;
        if (cuotaEstimada != null
                && gastosFijos != null
                && deudaInternaBanco != null
                && deudaCirbeMensual != null) {
            totalCompromisos = cuotaEstimada + gastosFijos + deudaInternaBanco + deudaCirbeMensual;
        }

        // --- ratioEndeudamiento = totalCompromisos / ingresosNetosMensuales ---
        if (totalCompromisos != null && ingresos != null && ingresos != 0.0) {
            calc.setRatioEndeudamiento(totalCompromisos / ingresos);
        }

        // --- remanenteSubsistencia = ingresos - totalCompromisos ---
        if (totalCompromisos != null && ingresos != null) {
            calc.setRemanenteSubsistencia(ingresos - totalCompromisos);
        }

        // --- edadAlVencimiento = edad + (plazoMeses / 12) ---
        Integer edad = datosCore.getEdad();
        Integer plazoMeses = datosUsuario.getPlazoMeses();
        if (edad != null && plazoMeses != null) {
            // División entera intencionada (años completos, como indica el SYSTEM_SPEC)
            calc.setEdadAlVencimiento(edad + (plazoMeses / 12));
        }

        return calc;
    }
}
