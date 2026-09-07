package com.example.demo.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.ArrayList;
import java.util.List;

/**
 * DTO de salida del motor de reglas Drools.
 * Contiene el resultado de la evaluación, las reglas disparadas, los textos legales
 * y el tono recomendado para la respuesta al usuario.
 * El estado se inicializa a "EN_PROCESO" para habilitar la condición de guarda anticolisión en DRL.
 */
public class ResultadoEvaluacion {

    /**
     * Estado de la evaluación:
     * EN_PROCESO | REQUIERE_DATOS | REQUIERE_ACCION | REQUIERE_SUPERVISION_HUMANA | DENEGADO | APROBADO
     * Inicializado a "EN_PROCESO" para que las reglas DRL evalúen la condición de guarda.
     */
    private String estado = "EN_PROCESO";

    /** Lista de nombres de reglas que se han disparado durante la evaluación. */
    @JsonProperty("reglas_disparadas")
    private List<String> reglasDisparadas = new ArrayList<>();

    /** Acción requerida al sistema orquestador (p.ej. "CONSULTAR_CIRBE_ASNEF"). Null si no aplica. */
    @JsonProperty("accion_requerida")
    private String accionRequerida;

    /** Dato que falta para continuar la evaluación (p.ej. "proposito"). Null si no aplica. */
    @JsonProperty("dato_faltante")
    private String datoFaltante;

    /** Artículo normativo asociado a la regla disparada. */
    @JsonProperty("articulo_normativo")
    private String articuloNormativo;

    /** Texto legal explicativo de la decisión tomada. */
    @JsonProperty("texto_legal")
    private String textoLegal;

    /**
     * Tono recomendado para la respuesta generada por el NLG.
     * Serializado como "tono_mensaje" para alinearse con el esquema Python DroolsResponse.
     */
    @JsonProperty("tono_mensaje")
    private String tono;

    /** Cálculos derivados asociados a la evaluación (calculados antes de ejecutar Drools). */
    @JsonProperty("calculos_derivados")
    private CalculosDerivados calculosDerivados;

    // =========================================================
    // Constructor sin argumentos
    // =========================================================
    public ResultadoEvaluacion() {
    }

    // =========================================================
    // Constructor completo
    // =========================================================
    public ResultadoEvaluacion(String estado, List<String> reglasDisparadas,
                               String accionRequerida, String datoFaltante,
                               String articuloNormativo, String textoLegal,
                               String tono, CalculosDerivados calculosDerivados) {
        this.estado = estado;
        this.reglasDisparadas = reglasDisparadas != null ? reglasDisparadas : new ArrayList<>();
        this.accionRequerida = accionRequerida;
        this.datoFaltante = datoFaltante;
        this.articuloNormativo = articuloNormativo;
        this.textoLegal = textoLegal;
        this.tono = tono;
        this.calculosDerivados = calculosDerivados;
    }

    // =========================================================
    // Getters y Setters
    // =========================================================

    public String getEstado() {
        return estado;
    }

    public void setEstado(String estado) {
        this.estado = estado;
    }

    public List<String> getReglasDisparadas() {
        return reglasDisparadas;
    }

    public void setReglasDisparadas(List<String> reglasDisparadas) {
        this.reglasDisparadas = reglasDisparadas;
    }

    public String getAccionRequerida() {
        return accionRequerida;
    }

    public void setAccionRequerida(String accionRequerida) {
        this.accionRequerida = accionRequerida;
    }

    public String getDatoFaltante() {
        return datoFaltante;
    }

    public void setDatoFaltante(String datoFaltante) {
        this.datoFaltante = datoFaltante;
    }

    public String getArticuloNormativo() {
        return articuloNormativo;
    }

    public void setArticuloNormativo(String articuloNormativo) {
        this.articuloNormativo = articuloNormativo;
    }

    public String getTextoLegal() {
        return textoLegal;
    }

    public void setTextoLegal(String textoLegal) {
        this.textoLegal = textoLegal;
    }

    public String getTono() {
        return tono;
    }

    public void setTono(String tono) {
        this.tono = tono;
    }

    public CalculosDerivados getCalculosDerivados() {
        return calculosDerivados;
    }

    public void setCalculosDerivados(CalculosDerivados calculosDerivados) {
        this.calculosDerivados = calculosDerivados;
    }

    @Override
    public String toString() {
        return "ResultadoEvaluacion{" +
                "estado='" + estado + '\'' +
                ", reglasDisparadas=" + reglasDisparadas +
                ", accionRequerida='" + accionRequerida + '\'' +
                ", datoFaltante='" + datoFaltante + '\'' +
                ", articuloNormativo='" + articuloNormativo + '\'' +
                ", textoLegal='" + textoLegal + '\'' +
                ", tono='" + tono + '\'' +
                ", calculosDerivados=" + calculosDerivados +
                '}';
    }
}
