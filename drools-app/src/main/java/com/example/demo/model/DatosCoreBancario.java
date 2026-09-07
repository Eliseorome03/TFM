package com.example.demo.model;

/**
 * Datos del core bancario del cliente, obtenidos del sistema interno del banco.
 * Todos los atributos usan tipos Wrapper para permitir evaluación de nulos en las reglas DRL.
 */
public class DatosCoreBancario {

    /** Identificador único del cliente en el sistema bancario. */
    private String clienteId;

    /** DNI del cliente. */
    private String dni;

    /** Edad actual del cliente en años. */
    private Integer edad;

    /** Ingresos netos mensuales del cliente en euros. */
    private Double ingresosNetosMensuales;

    /** Antigüedad del cliente en el banco, expresada en meses. */
    private Integer antiguedadMeses;

    /** Importe mensual de deuda interna con el banco (préstamos previos, etc.). */
    private Double deudaInternaBancoMensual;

    /** Indica si el cliente actúa como avalista de alguna empresa. */
    private Boolean esAvalista;

    /** CIF de la empresa avalada, si el cliente es avalista. Null en caso contrario. */
    private String empresaAvaladaCif;

    // =========================================================
    // Constructor sin argumentos (requerido por Jackson/Drools)
    // =========================================================
    public DatosCoreBancario() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public DatosCoreBancario(String clienteId, String dni, Integer edad,
                             Double ingresosNetosMensuales, Integer antiguedadMeses,
                             Double deudaInternaBancoMensual, Boolean esAvalista,
                             String empresaAvaladaCif) {
        this.clienteId = clienteId;
        this.dni = dni;
        this.edad = edad;
        this.ingresosNetosMensuales = ingresosNetosMensuales;
        this.antiguedadMeses = antiguedadMeses;
        this.deudaInternaBancoMensual = deudaInternaBancoMensual;
        this.esAvalista = esAvalista;
        this.empresaAvaladaCif = empresaAvaladaCif;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public String getClienteId() {
        return clienteId;
    }

    public void setClienteId(String clienteId) {
        this.clienteId = clienteId;
    }

    public String getDni() {
        return dni;
    }

    public void setDni(String dni) {
        this.dni = dni;
    }

    public Integer getEdad() {
        return edad;
    }

    public void setEdad(Integer edad) {
        this.edad = edad;
    }

    public Double getIngresosNetosMensuales() {
        return ingresosNetosMensuales;
    }

    public void setIngresosNetosMensuales(Double ingresosNetosMensuales) {
        this.ingresosNetosMensuales = ingresosNetosMensuales;
    }

    public Integer getAntiguedadMeses() {
        return antiguedadMeses;
    }

    public void setAntiguedadMeses(Integer antiguedadMeses) {
        this.antiguedadMeses = antiguedadMeses;
    }

    public Double getDeudaInternaBancoMensual() {
        return deudaInternaBancoMensual;
    }

    public void setDeudaInternaBancoMensual(Double deudaInternaBancoMensual) {
        this.deudaInternaBancoMensual = deudaInternaBancoMensual;
    }

    public Boolean getEsAvalista() {
        return esAvalista;
    }

    public void setEsAvalista(Boolean esAvalista) {
        this.esAvalista = esAvalista;
    }

    public String getEmpresaAvaladaCif() {
        return empresaAvaladaCif;
    }

    public void setEmpresaAvaladaCif(String empresaAvaladaCif) {
        this.empresaAvaladaCif = empresaAvaladaCif;
    }

    @Override
    public String toString() {
        return "DatosCoreBancario{" +
                "clienteId='" + clienteId + '\'' +
                ", dni='" + dni + '\'' +
                ", edad=" + edad +
                ", ingresosNetosMensuales=" + ingresosNetosMensuales +
                ", antiguedadMeses=" + antiguedadMeses +
                ", deudaInternaBancoMensual=" + deudaInternaBancoMensual +
                ", esAvalista=" + esAvalista +
                ", empresaAvaladaCif='" + empresaAvaladaCif + '\'' +
                '}';
    }
}
