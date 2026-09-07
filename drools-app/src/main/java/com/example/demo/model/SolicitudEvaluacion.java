package com.example.demo.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * DTO de entrada al endpoint POST /api/evaluate.
 * Agrega los tres bloques de datos necesarios para la evaluación de préstamos.
 */
public class SolicitudEvaluacion {

    /** Datos aportados por el usuario durante el proceso conversacional. */
    @JsonProperty("datos_usuario")
    private DatosUsuario datosUsuario;

    /**
     * Datos del core bancario del cliente (obtenidos del sistema interno).
     * JSON key: "datos_core" (alineado con DroolsRequest.datos_core del backend Python).
     */
    @JsonProperty("datos_core")
    private DatosCoreBancario datosCoreBancario;

    /**
     * Datos externos del Banco de España: CIRBE y ASNEF.
     * JSON key: "datos_bde" (alineado con DroolsRequest.datos_bde del backend Python).
     */
    @JsonProperty("datos_bde")
    private DatosExternosBde datosExternosBde;

    // =========================================================
    // Constructor sin argumentos (requerido por Jackson)
    // =========================================================
    public SolicitudEvaluacion() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public SolicitudEvaluacion(DatosUsuario datosUsuario, DatosCoreBancario datosCoreBancario,
                               DatosExternosBde datosExternosBde) {
        this.datosUsuario = datosUsuario;
        this.datosCoreBancario = datosCoreBancario;
        this.datosExternosBde = datosExternosBde;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public DatosUsuario getDatosUsuario() {
        return datosUsuario;
    }

    public void setDatosUsuario(DatosUsuario datosUsuario) {
        this.datosUsuario = datosUsuario;
    }

    public DatosCoreBancario getDatosCoreBancario() {
        return datosCoreBancario;
    }

    public void setDatosCoreBancario(DatosCoreBancario datosCoreBancario) {
        this.datosCoreBancario = datosCoreBancario;
    }

    public DatosExternosBde getDatosExternosBde() {
        return datosExternosBde;
    }

    public void setDatosExternosBde(DatosExternosBde datosExternosBde) {
        this.datosExternosBde = datosExternosBde;
    }

    @Override
    public String toString() {
        return "SolicitudEvaluacion{" +
                "datosUsuario=" + datosUsuario +
                ", datosCoreBancario=" + datosCoreBancario +
                ", datosExternosBde=" + datosExternosBde +
                '}';
    }
}
