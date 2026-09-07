package com.example.demo.model;

/**
 * Datos aportados por el usuario durante el proceso conversacional.
 * Todos los atributos usan tipos Wrapper para permitir evaluación de nulos en las reglas DRL.
 */
public class DatosUsuario {

    /** Intención principal detectada por el NLU: SOLICITAR_PRESTAMO, CONSULTAR_DUDA, SALUDAR, OTRA */
    private String intencionPrincipal;

    /** Cantidad solicitada en euros. Puede ser null si no ha sido proporcionada. */
    private Double cantidadSolicitada;

    /** Plazo en meses. Puede ser null si no ha sido proporcionado. */
    private Integer plazoMeses;

    /**
     * Propósito del préstamo: VEHICULO, REFORMA, ESTUDIOS, SALUD, OTRO,
     * CRIPTOMONEDAS, APUESTAS, REFINANCIACION_INFORMAL. Null si no proporcionado.
     */
    private String proposito;

    /** Gastos fijos mensuales (alquiler, suministros, etc.). Null si no proporcionados. */
    private Double gastosFijosMensuales;

    /** Deuda declarada por el usuario. Null si no proporcionada. */
    private Double deudaDeclarada;

    /** Categoría de duda del usuario catch-all: NINGUNA, REQUISITOS_APROBACION, etc. */
    private String dudaCatchAll;

    // =========================================================
    // Constructor sin argumentos (requerido por Jackson/Drools)
    // =========================================================
    public DatosUsuario() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public DatosUsuario(String intencionPrincipal, Double cantidadSolicitada, Integer plazoMeses,
                        String proposito, Double gastosFijosMensuales, Double deudaDeclarada,
                        String dudaCatchAll) {
        this.intencionPrincipal = intencionPrincipal;
        this.cantidadSolicitada = cantidadSolicitada;
        this.plazoMeses = plazoMeses;
        this.proposito = proposito;
        this.gastosFijosMensuales = gastosFijosMensuales;
        this.deudaDeclarada = deudaDeclarada;
        this.dudaCatchAll = dudaCatchAll;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public String getIntencionPrincipal() {
        return intencionPrincipal;
    }

    public void setIntencionPrincipal(String intencionPrincipal) {
        this.intencionPrincipal = intencionPrincipal;
    }

    public Double getCantidadSolicitada() {
        return cantidadSolicitada;
    }

    public void setCantidadSolicitada(Double cantidadSolicitada) {
        this.cantidadSolicitada = cantidadSolicitada;
    }

    public Integer getPlazoMeses() {
        return plazoMeses;
    }

    public void setPlazoMeses(Integer plazoMeses) {
        this.plazoMeses = plazoMeses;
    }

    public String getProposito() {
        return proposito;
    }

    public void setProposito(String proposito) {
        this.proposito = proposito;
    }

    public Double getGastosFijosMensuales() {
        return gastosFijosMensuales;
    }

    public void setGastosFijosMensuales(Double gastosFijosMensuales) {
        this.gastosFijosMensuales = gastosFijosMensuales;
    }

    public Double getDeudaDeclarada() {
        return deudaDeclarada;
    }

    public void setDeudaDeclarada(Double deudaDeclarada) {
        this.deudaDeclarada = deudaDeclarada;
    }

    public String getDudaCatchAll() {
        return dudaCatchAll;
    }

    public void setDudaCatchAll(String dudaCatchAll) {
        this.dudaCatchAll = dudaCatchAll;
    }

    @Override
    public String toString() {
        return "DatosUsuario{" +
                "intencionPrincipal='" + intencionPrincipal + '\'' +
                ", cantidadSolicitada=" + cantidadSolicitada +
                ", plazoMeses=" + plazoMeses +
                ", proposito='" + proposito + '\'' +
                ", gastosFijosMensuales=" + gastosFijosMensuales +
                ", deudaDeclarada=" + deudaDeclarada +
                ", dudaCatchAll='" + dudaCatchAll + '\'' +
                '}';
    }
}
