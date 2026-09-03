# Especificación del Sistema Neurosimbólico Bancario

## 1. Visión General del Proyecto y Principios Arquitectónicos

El objetivo de este sistema es evaluar solicitudes de préstamos personales combinando la flexibilidad conversacional de un modelo neuronal (**Mistral**) con el determinismo, trazabilidad y gobernanza de un motor de reglas simbólico (**Drools**). Todo el diseño responde a las exigencias regulatorias de la **Directiva 2014/17/UE** y del **EU AI Act** para sistemas de alto riesgo.

* **Paradigma Arquitectónico (Kautz Nivel 1-2: Symbolic[Neuro]):** El componente simbólico (código backend + Drools) gobierna y orquesta. El componente neuronal (Mistral) opera como servicio encapsulado para dos tareas lingüísticas estrictas: extracción estructurada (NLU) y redacción fiel (NLG).
* **Information State Update (ISU):** El contexto conversacional y de negocio no reside en la ventana de tokens del LLM, sino en una estructura formal inmutable (`information_state`) gestionada paso a paso.
* **Explicabilidad Constitutiva:** La justificación legal y fáctica de una decisión no se genera post-hoc como una racionalización del LLM. La traza literal de las reglas disparadas en Drools constituye la explicación auditable por construcción.
* **RAG Simbólico Gobernado:** Se prescinde de búsqueda vectorial heurística. Las referencias legales (Directiva 2014/17/UE, Código Civil, etc.) están indexadas formalmente por Drools y se devuelven asociadas a la regla que las detona.
* **Mitigación de Prompt Injection (Read-Only State Dump):** El LLM de salida (NLG) carece de herramientas de ejecución. Recibe el volcado del estado emitido por Drools en modo solo lectura, neutralizando el impacto transaccional de ataques de inyección.

---

## 2. Contrato Canónico de Datos: `information_state`

Este esquema JSON define la verdad del sistema en cualquier instante del diálogo.

```json
{
  "session_id": "string (UUID)",
  "turn_id": "integer",
  "datos_usuario": {
    "cantidad_solicitada": "float | null",
    "plazo_meses": "integer | null",
    "proposito": "string | null",
    "regimen_vivienda": "string | null",
    "gasto_alquiler": "float | null",
    "deuda_declarada": "float | null",
    "duda_catch_all": "string | null"
  },
  "datos_core_bancario": {
    "cliente_id": "string",
    "dni": "string",
    "edad": "integer",
    "ingresos_netos_mensuales": "float",
    "antiguedad_meses": "integer",
    "deuda_interna_banco": "float",
    "es_avalista_solidario": "boolean",
    "empresa_avalada_cif": "string | null"
  },
  "datos_externos_bde": {
    "consultado": "boolean",
    "tiene_impagos_activos": "boolean",
    "importe_morosidad_asnef": "float",
    "deuda_cirbe": "float",
    "empresa_avalada_concurso": "boolean"
  },
  "calculos_derivados": {
    "cuota_estimada": "float",
    "ratio_endeudamiento": "float",
    "remanente_subsistencia": "float",
    "edad_al_vencimiento": "integer"
  },
  "evaluacion_drools": {
    "estado": "string (EN_PROCESO | REQUIERE_DATOS | REQUIERE_ACCION | REQUIERE_SUPERVISION_HUMANA | DENEGADO | APROBADO)",
    "reglas_disparadas": ["string"],
    "accion_requerida": "string | null",
    "dato_faltante": "string | null",
    "articulo_normativo": "string | null",
    "texto_legal": "string | null"
  }
}
```

---

## 3. Esquemas de Intercambio

### 3.1. Entrada a Drools (`POST /evaluar`)

Drools recibe una versión aplanada o anidada de los datos consolidados:
* Campos numéricos y descriptivos de `datos_usuario` y `datos_core_bancario`.
* Campos de `datos_externos_bde`.

### 3.2. Salida de Drools

```json
{
  "estado": "DENEGADO",
  "reglas_disparadas": ["R_RATIO_ENDEUDAMIENTO"],
  "accion_requerida": null,
  "dato_faltante": null,
  "calculos_derivados": {
    "cuota_estimada": 250.0,
    "ratio_endeudamiento": 0.45,
    "remanente_subsistencia": 1050.0,
    "edad_al_vencimiento": 36
  },
  "articulo_normativo": "Art. 18 Directiva 2014/17/UE",
  "texto_legal": "El prestamista solo pondrá el crédito a disposición del consumidor si el resultado de la evaluación de solvencia indica que es probable que las obligaciones sean satisfechas."
}
```

### 3.3. Salida de NLU Mistral (`EsquemaNLU`)

```json
{
  "intencion_principal": "solicitar_prestamo | consultar_duda | saludar | desconocida",
  "cantidad_solicitada": 12000.0,
  "plazo_meses": 48,
  "proposito": "vehiculo",
  "regimen_vivienda": "ALQUILER",
  "gasto_alquiler": 650.0,
  "deuda_declarada": 0.0,
  "duda_catch_all": null
}
```

---

## 4. Catálogo de Reglas en Drools DRL

| Regla | Prioridad (*Salience*) | Condición Lógica | Estado Resultante / Acción | Justificación Normativa |
| :--- | :---: | :--- | :--- | :--- |
| `R_VALIDACION_ALQUILER` | 100 | `regimen_vivienda == "ALQUILER" && (gasto_alquiler == null \|\| gasto_alquiler <= 0)` | `REQUIERE_DATOS`<br>`dato_faltante: "gasto_alquiler"` | Obligación de comprobación rigurosa de gastos fijos |
| `R_PROPOSITO_NO_FINANCIABLE` | 90 | `proposito in ("CRIPTOMONEDAS", "APUESTAS", "REFINANCIACION_INFORMAL")` | `DENEGADO` | Ley 10/2010 PBC y directrices EBA sobre originación de crédito prudencial |
| `R_EDAD_VENCIMIENTO` | 80 | `edad < 18 \|\| (edad + (plazo_meses / 12)) > 75` | `DENEGADO` | Criterios de capacidad legal y riesgo actuarial por edad |
| `R_DISPARAR_CIRBE` | 70 | `datos_externos_bde.consultado == false` | `REQUIERE_ACCION`<br>`accion_requerida: "CONSULTAR_CIRBE_ASNEF"` | Obligación regulatoria de consulta previa a ficheros de solvencia patrimonial |
| `R_MOROSIDAD_ASNEF` | 60 | `tiene_impagos_activos == true \|\| importe_morosidad_asnef > 0` | `DENEGADO` | Criterios prudenciales de morosidad crediticia |
| `R_ALERTA_QUIEBRA_AVAL` | 50 | `es_avalista_solidario == true && empresa_avalada_concurso == true` | `DENEGADO` | Riesgo concursal indirecto exigible a corto plazo (Criterios EBA) |
| `R_DISCREPANCIA_DECLARADA` | 40 | `deuda_cirbe > (deuda_declarada * 1.35)` | `REQUIERE_SUPERVISION_HUMANA` | Art. 14 EU AI Act (Supervisión humana ante anomalías no resueltas) |
| `R_RATIO_ENDEUDAMIENTO` | 30 | `ratio_endeudamiento > 0.40` | `DENEGADO` | Directiva 2014/17/UE y Banco de España (Límite máximo del 40% de endeudamiento) |
| `R_MINIMO_SUBSISTENCIA` | 20 | `remanente_subsistencia < 700.0` | `DENEGADO` | Art. 607 LEC (Mínimo vital inembargable derivado del SMI) |
| `R_APROBACION_ESTANDAR` | 10 | Sin alertas morosas, `ratio <= 0.35`, `remanente >= 700` | `APROBADO` | Art. 18.1 Directiva 2014/17/UE (Capacidad positiva comprobada) |

### Fórmulas de derivación ejecutadas previamente en Drools o en el motor de cálculo:

$$
\text{cuota\_estimada} = \frac{\text{cantidad\_solicitada}}{\text{plazo\_meses}}
$$

$$
\text{ratio\_endeudamiento} = \frac{\text{cuota\_estimada} + \text{gasto\_alquiler} + \text{deuda\_interna\_banco} + \text{deuda\_cirbe}}{\text{ingresos\_netos\_mensuales}}
$$

$$
\text{remanente\_subsistencia} = \text{ingresos\_netos\_mensuales} - (\text{cuota\_estimada} + \text{gasto\_alquiler} + \text{deuda\_interna\_banco} + \text{deuda\_cirbe})
$$

$$
\text{edad\_al\_vencimiento} = \text{edad} + \frac{\text{plazo\_meses}}{12}
$$

---

## 5. El Flujo de Ejecución por Pasos (Auditoría AI Act)

Cada turno conversacional ejecuta hasta 7 micro-acciones registradas individualmente en `trazas_auditoria`:

1. **`EXTRACT_NLU`**: Mistral procesa el mensaje del usuario y devuelve `EsquemaNLU`.
2. **`FETCH_CORE_DATA`**: FastAPI extrae el registro de la tabla `clientes` para el cliente seleccionado.
3. **`EVALUATE_PRELIMINARY`**: Drools evalúa los datos reunidos.
4. **`FETCH_CIRBE_ASNEF`** *(Condicional)*: Si Drools devuelve `REQUIERE_ACCION`, FastAPI consulta el mock del Banco de España (CIRBE / ASNEF).
5. **`EVALUATE_FINAL_DECISION`** *(Condicional)*: Drools reevalúa con los datos del mock inyectados.
6. **`GENERATE_NATURAL_RESPONSE`**: Mistral recibe el `information_state` final en modo solo lectura y genera la respuesta textual.
7. **`PERSIST_STATE`**: Registro del snapshot final de la interacción y de la traza para auditoría.