package com.example.demo.model;

/**
 * Datos externos del Banco de España (BdE): CIRBE y ASNEF.
 * Todos los atributos usan tipos Wrapper para permitir evaluación de nulos en las reglas DRL.
 */
public class DatosExternosBde {

    /** Indica si ya se ha realizado la consulta al BdE (CIRBE/ASNEF). */
    private Boolean consultado;

    /** Indica si el cliente tiene impagos activos en ASNEF. */
    private Boolean tieneImpagosActivos;

    /** Importe total de morosidad registrado en ASNEF en euros. */
    private Double importeMorosidadAsnef;

    /** Indica si la empresa avalada se encuentra en concurso de acreedores. Null si no es avalista. */
    private Boolean empresaAvaladaConcurso;

    /** Deuda mensual registrada en CIRBE (compromisos periódicos). */
    private Double deudaCirbeMensual;

    /** Deuda total acumulada registrada en CIRBE. */
    private Double deudaCirbeTotal;

    // =========================================================
    // Constructor sin argumentos (requerido por Jackson/Drools)
    // =========================================================
    public DatosExternosBde() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public DatosExternosBde(Boolean consultado, Boolean tieneImpagosActivos,
                            Double importeMorosidadAsnef, Boolean empresaAvaladaConcurso,
                            Double deudaCirbeMensual, Double deudaCirbeTotal) {
        this.consultado = consultado;
        this.tieneImpagosActivos = tieneImpagosActivos;
        this.importeMorosidadAsnef = importeMorosidadAsnef;
        this.empresaAvaladaConcurso = empresaAvaladaConcurso;
        this.deudaCirbeMensual = deudaCirbeMensual;
        this.deudaCirbeTotal = deudaCirbeTotal;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public Boolean getConsultado() {
        return consultado;
    }

    public void setConsultado(Boolean consultado) {
        this.consultado = consultado;
    }

    public Boolean getTieneImpagosActivos() {
        return tieneImpagosActivos;
    }

    public void setTieneImpagosActivos(Boolean tieneImpagosActivos) {
        this.tieneImpagosActivos = tieneImpagosActivos;
    }

    public Double getImporteMorosidadAsnef() {
        return importeMorosidadAsnef;
    }

    public void setImporteMorosidadAsnef(Double importeMorosidadAsnef) {
        this.importeMorosidadAsnef = importeMorosidadAsnef;
    }

    public Boolean getEmpresaAvaladaConcurso() {
        return empresaAvaladaConcurso;
    }

    public void setEmpresaAvaladaConcurso(Boolean empresaAvaladaConcurso) {
        this.empresaAvaladaConcurso = empresaAvaladaConcurso;
    }

    public Double getDeudaCirbeMensual() {
        return deudaCirbeMensual;
    }

    public void setDeudaCirbeMensual(Double deudaCirbeMensual) {
        this.deudaCirbeMensual = deudaCirbeMensual;
    }

    public Double getDeudaCirbeTotal() {
        return deudaCirbeTotal;
    }

    public void setDeudaCirbeTotal(Double deudaCirbeTotal) {
        this.deudaCirbeTotal = deudaCirbeTotal;
    }

    @Override
    public String toString() {
        return "DatosExternosBde{" +
                "consultado=" + consultado +
                ", tieneImpagosActivos=" + tieneImpagosActivos +
                ", importeMorosidadAsnef=" + importeMorosidadAsnef +
                ", empresaAvaladaConcurso=" + empresaAvaladaConcurso +
                ", deudaCirbeMensual=" + deudaCirbeMensual +
                ", deudaCirbeTotal=" + deudaCirbeTotal +
                '}';
    }
}
