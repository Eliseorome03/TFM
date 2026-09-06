"""
schemas/drools_io.py — DTOs tipados de intercambio con el microservicio Drools.

Define los modelos de entrada (`DroolsRequest`) y salida (`DroolsResponse`)
para las llamadas HTTP POST al endpoint /api/evaluate del servicio drools-app.

El payload refleja la estructura de objetos Java esperada por Spring Boot + KIE.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DroolsDatosUsuario(BaseModel):
    """Datos extraídos por NLU enviados a Drools."""

    intencion_principal: str | None = Field(default=None)
    cantidad_solicitada: float | None = Field(default=None)
    plazo_meses: int | None = Field(default=None)
    proposito: str | None = Field(default=None)
    gastos_fijos_mensuales: float | None = Field(default=None)
    deuda_declarada: float | None = Field(default=None)
    duda_catch_all: str = Field(default="NINGUNA")


class DroolsDatosCore(BaseModel):
    """Datos del perfil bancario core enviados a Drools."""

    cliente_id: str | None = Field(default=None)
    dni: str | None = Field(default=None)
    edad: int | None = Field(default=None)
    ingresos_netos_mensuales: float | None = Field(default=None)
    antiguedad_meses: int | None = Field(default=None)
    deuda_interna_banco_mensual: float | None = Field(default=None)
    es_avalista: bool = Field(default=False)
    empresa_avalada_cif: str | None = Field(default=None)


class DroolsDatosBde(BaseModel):
    """Datos externos del BdE (CIRBE/ASNEF) enviados a Drools."""

    consultado: bool = Field(default=False)
    tiene_impagos_activos: bool = Field(default=False)
    importe_morosidad_asnef: float = Field(default=0.0)
    empresa_avalada_concurso: bool | None = Field(default=None)
    deuda_cirbe_mensual: float = Field(default=0.0)
    deuda_cirbe_total: float = Field(default=0.0)


class DroolsRequest(BaseModel):
    """
    Payload de entrada para el endpoint POST /api/evaluate de Drools.

    Agrega los tres bloques de datos: usuario, core bancario y BdE.
    """

    datos_usuario: DroolsDatosUsuario = Field(default_factory=DroolsDatosUsuario)
    datos_core: DroolsDatosCore = Field(default_factory=DroolsDatosCore)
    datos_bde: DroolsDatosBde = Field(default_factory=DroolsDatosBde)


class DroolsCalculosDerivados(BaseModel):
    """Cálculos financieros calculados por Drools y devueltos en la respuesta."""

    cuota_estimada: float | None = Field(default=None)
    ratio_endeudamiento: float | None = Field(default=None)
    remanente_subsistencia: float | None = Field(default=None)
    edad_al_vencimiento: int | None = Field(default=None)


class DroolsResponse(BaseModel):
    """
    Respuesta del motor de reglas Drools tras evaluar una solicitud.

    Contiene la decisión normativa, las reglas disparadas, la justificación legal
    y los cálculos financieros derivados.

    Ejemplo de respuesta para denegación por ratio de endeudamiento:
    {
        "estado": "DENEGADO",
        "reglas_disparadas": ["R_RATIO_ENDEUDAMIENTO"],
        "accion_requerida": null,
        "dato_faltante": null,
        "calculos_derivados": {...},
        "articulo_normativo": "Art. 18 Directiva 2014/17/UE",
        "texto_legal": "El ratio máximo de endeudamiento no debe exceder...",
        "tono_mensaje": "firme, claro y respetuoso"
    }
    """

    estado: str = Field(..., description="Estado resultante de la evaluación Drools")
    reglas_disparadas: list[str] = Field(
        default_factory=list,
        description="Lista de identificadores de reglas que se activaron",
    )
    accion_requerida: str | None = Field(
        default=None,
        description="Acción que debe ejecutar el backend (ej: 'CONSULTAR_CIRBE_ASNEF')",
    )
    dato_faltante: str | None = Field(
        default=None,
        description="Nombre del campo que Drools necesita para continuar la evaluación",
    )
    calculos_derivados: DroolsCalculosDerivados | None = Field(
        default=None,
        description="Cálculos financieros realizados por Drools",
    )
    articulo_normativo: str | None = Field(
        default=None,
        description="Referencia legal asociada a la regla que tomó la decisión",
    )
    texto_legal: str | None = Field(
        default=None,
        description="Texto íntegro del artículo normativo aplicado",
    )
    tono_mensaje: str | None = Field(
        default=None,
        description="Tono recomendado para la respuesta NLG según la regla disparada",
    )
