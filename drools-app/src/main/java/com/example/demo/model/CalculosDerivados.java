package com.example.demo.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Cálculos derivados ejecutados por el servicio antes de insertar los facts en la sesión Drools.
 * Todos los atributos usan tipos Wrapper para permitir evaluación de nulos en las reglas DRL.
 *
 * Fórmulas:
 *   cuotaEstimada         = cantidadSolicitada / plazoMeses
 *   ratioEndeudamiento    = (cuotaEstimada + gastosFijosMensuales + deudaInternaBancoMensual + deudaCirbeMensual) / ingresosNetosMensuales
 *   remanenteSubsistencia = ingresosNetosMensuales - (cuotaEstimada + gastosFijosMensuales + deudaInternaBancoMensual + deudaCirbeMensual)
 *   edadAlVencimiento     = edad + (plazoMeses / 12)
 */
public class CalculosDerivados {

    /** Cuota mensual estimada del préstamo en euros. Null si datos insuficientes. */
    @JsonProperty("cuota_estimada")
    private Double cuotaEstimada;

    /** Ratio de endeudamiento (0.0 - 1.0+). Null si datos insuficientes. */
    @JsonProperty("ratio_endeudamiento")
    private Double ratioEndeudamiento;

    /** Remanente mensual tras compromisos de pago en euros. Null si datos insuficientes. */
    @JsonProperty("remanente_subsistencia")
    private Double remanenteSubsistencia;

    /** Edad del cliente al vencimiento del préstamo. Null si datos insuficientes. */
    @JsonProperty("edad_al_vencimiento")
    private Integer edadAlVencimiento;

    // =========================================================
    // Constructor sin argumentos (requerido por Jackson/Drools)
    // =========================================================
    public CalculosDerivados() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public CalculosDerivados(Double cuotaEstimada, Double ratioEndeudamiento,
                             Double remanenteSubsistencia, Integer edadAlVencimiento) {
        this.cuotaEstimada = cuotaEstimada;
        this.ratioEndeudamiento = ratioEndeudamiento;
        this.remanenteSubsistencia = remanenteSubsistencia;
        this.edadAlVencimiento = edadAlVencimiento;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public Double getCuotaEstimada() {
        return cuotaEstimada;
    }

    public void setCuotaEstimada(Double cuotaEstimada) {
        this.cuotaEstimada = cuotaEstimada;
    }

    public Double getRatioEndeudamiento() {
        return ratioEndeudamiento;
    }

    public void setRatioEndeudamiento(Double ratioEndeudamiento) {
        this.ratioEndeudamiento = ratioEndeudamiento;
    }

    public Double getRemanenteSubsistencia() {
        return remanenteSubsistencia;
    }

    public void setRemanenteSubsistencia(Double remanenteSubsistencia) {
        this.remanenteSubsistencia = remanenteSubsistencia;
    }

    public Integer getEdadAlVencimiento() {
        return edadAlVencimiento;
    }

    public void setEdadAlVencimiento(Integer edadAlVencimiento) {
        this.edadAlVencimiento = edadAlVencimiento;
    }

    @Override
    public String toString() {
        return "CalculosDerivados{" +
                "cuotaEstimada=" + cuotaEstimada +
                ", ratioEndeudamiento=" + ratioEndeudamiento +
                ", remanenteSubsistencia=" + remanenteSubsistencia +
                ", edadAlVencimiento=" + edadAlVencimiento +
                '}';
    }
}
