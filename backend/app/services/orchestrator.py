"""
services/orchestrator.py — Orquestador del pipeline conversacional de 6 pasos.

Implementa la clase `PipelineOrchestrator` que ejecuta los 6 micro-acciones
secuenciales definidas en SYSTEM_SPEC.md § 5, registrando cada una en el
ledger de auditoría mediante `AuditTracker`.

Pipeline por turno conversacional:
  1. EXTRACT_NLU         — Mistral extrae entidades del mensaje del usuario.
  2. FETCH_CORE_DATA     — FastAPI consulta la tabla 'clientes' (solo turno 1).
  3. EVALUATE_PRELIMINARY — Drools evalúa con los datos disponibles.
  4. FETCH_CIRBE_ASNEF   — (Condicional) BdE mock si Drools pide CONSULTAR_CIRBE_ASNEF.
  5. EVALUATE_FINAL_DECISION — (Condicional) Drools reevalúa con datos BdE.
  6. GENERATE_NATURAL_RESPONSE — Mistral genera la respuesta textual (read-only).

Paradigma ISU (Information State Update):
  El `information_state` se inicializa en el primer turno y se actualiza
  acumulativamente: los datos de turnos anteriores se preservan y los nuevos
  se sobreescriben o completan, nunca se borran los ya conocidos.
"""

import logging
from sqlalchemy.orm import Session

from app.clients.mistral_client import MistralClient
from app.clients.drools_client import DroolsClient
from app.models.cliente import ClienteModel
from app.schemas.state import (
    InformationState,
    DatosUsuario,
    DatosCoreBancario,
    DatosExternosBde,
    CalculosDerivados,
    EvaluacionDrools,
    EstadoEvaluacion,
)
from app.services.audit_tracker import AuditTracker
from app.services.bde_mock_service import BdeMockService

logger = logging.getLogger(__name__)

# Cache en memoria de estados por session_id
# En producción se reemplazaría por Redis u otro almacén persistente
_session_states: dict[str, dict] = {}


class PipelineOrchestrator:
    """
    Orquestador del pipeline conversacional neurosimbólico.

    Ejecuta los 6 pasos secuenciales del ciclo por cada turno del usuario,
    manteniendo el InformationState entre turnos mediante caché en memoria.

    Cada micro-acción se registra de forma atómica en la tabla de auditoría
    antes de continuar al siguiente paso, garantizando trazabilidad total
    incluso ante fallos intermedios.

    Sigue el paradigma Symbolic[Neuro]: el código simbólico (este orquestador
    + Drools) gobierna; Mistral opera como servicio encapsulado sin autonomía.
    """

    def __init__(
        self,
        mistral_client: MistralClient,
        drools_client: DroolsClient,
        bde_service: BdeMockService,
    ) -> None:
        """
        Inicializa el orquestador con sus dependencias inyectadas.

        Args:
            mistral_client: Instancia del cliente Mistral para NLU/NLG.
            drools_client: Instancia del cliente Drools para evaluación de reglas.
            bde_service: Instancia del servicio mock del BdE para CIRBE/ASNEF.
        """
        self._mistral = mistral_client
        self._drools = drools_client
        self._bde = bde_service
        logger.info("PipelineOrchestrator inicializado")

    def _obtener_o_crear_estado(
        self, session_id: str, cliente_id: str
    ) -> tuple[InformationState, int]:
        """
        Recupera el estado existente o crea uno nuevo para la sesión.

        Args:
            session_id: UUID de la sesión conversacional.
            cliente_id: ID del cliente para el nuevo estado.

        Returns:
            tuple: (InformationState, turn_id) con el estado y el número de turno.
        """
        if session_id in _session_states:
            estado_dict = _session_states[session_id]
            estado = InformationState.model_validate(estado_dict)
            estado.turn_id += 1
            turn_id = estado.turn_id
            logger.info(
                "Estado existente recuperado para sesión %s — Turno %d",
                session_id[:8],
                turn_id,
            )
        else:
            estado = InformationState(session_id=session_id, turn_id=1)
            turn_id = 1
            logger.info(
                "Nuevo estado creado para sesión %s — Turno 1",
                session_id[:8],
            )
        return estado, turn_id

    def _persistir_estado(self, session_id: str, estado: InformationState) -> None:
        """Persiste el estado actualizado en la caché de sesiones."""
        _session_states[session_id] = estado.as_dict()

    def _actualizar_datos_usuario(
        self, estado: InformationState, nlu_resultado
    ) -> InformationState:
        """
        Actualiza los datos del usuario en el estado con los resultados del NLU.

        Implementa fusión acumulativa: los valores nulos no sobreescriben
        datos ya conocidos de turnos anteriores (paradigma ISU).

        Args:
            estado: Estado actual del sistema.
            nlu_resultado: Objeto EsquemaNLU devuelto por Mistral.

        Returns:
            InformationState: Estado con datos_usuario actualizados.
        """
        du = estado.datos_usuario

        # Solo sobreescribir si el NLU devuelve un valor no nulo
        estado.datos_usuario = DatosUsuario(
            intencion_principal=nlu_resultado.intencion_principal.value,
            cantidad_solicitada=nlu_resultado.cantidad_solicitada
                if nlu_resultado.cantidad_solicitada is not None
                else du.cantidad_solicitada,
            plazo_meses=nlu_resultado.plazo_meses
                if nlu_resultado.plazo_meses is not None
                else du.plazo_meses,
            proposito=nlu_resultado.proposito.value
                if nlu_resultado.proposito is not None
                else du.proposito,
            gastos_fijos_mensuales=nlu_resultado.gastos_fijos_mensuales
                if nlu_resultado.gastos_fijos_mensuales is not None
                else du.gastos_fijos_mensuales,
            deuda_declarada=nlu_resultado.deuda_declarada
                if nlu_resultado.deuda_declarada is not None
                else du.deuda_declarada,
            duda_catch_all=nlu_resultado.duda_catch_all.value,
        )
        return estado

    def _actualizar_datos_drools(
        self, estado: InformationState, drools_response
    ) -> InformationState:
        """
        Actualiza el InformationState con la respuesta de Drools.

        Actualiza tanto los cálculos derivados como la evaluación.

        Args:
            estado: Estado actual del sistema.
            drools_response: Objeto DroolsResponse devuelto por el motor de reglas.

        Returns:
            InformationState: Estado con evaluación Drools y cálculos actualizados.
        """
        if drools_response.calculos_derivados:
            calcs = drools_response.calculos_derivados
            estado.calculos_derivados = CalculosDerivados(
                cuota_estimada=calcs.cuota_estimada,
                ratio_endeudamiento=calcs.ratio_endeudamiento,
                remanente_subsistencia=calcs.remanente_subsistencia,
                edad_al_vencimiento=calcs.edad_al_vencimiento,
            )

        estado.evaluacion_drools = EvaluacionDrools(
            estado=EstadoEvaluacion(drools_response.estado),
            reglas_disparadas=drools_response.reglas_disparadas,
            accion_requerida=drools_response.accion_requerida,
            dato_faltante=drools_response.dato_faltante,
            articulo_normativo=drools_response.articulo_normativo,
            texto_legal=drools_response.texto_legal,
            tono_mensaje=drools_response.tono_mensaje,
        )
        return estado

    def procesar_turno_conversacional(
        self,
        mensaje: str,
        cliente_id: str,
        session_id: str,
        db: Session,
    ) -> tuple[str, dict]:
        """
        Ejecuta el pipeline completo de 6 pasos para un turno conversacional.

        Método principal del orquestador. Ejecuta los pasos secuencialmente,
        registra cada uno en la tabla de auditoría y devuelve la respuesta
        textual y el estado final del sistema.

        Args:
            mensaje: Texto libre del mensaje del usuario.
            cliente_id: Identificador del cliente seleccionado.
            session_id: UUID de la sesión conversacional.
            db: Sesión SQLAlchemy para acceso a BD y auditoría.

        Returns:
            tuple: (respuesta_texto: str, information_state: dict)
        """
        tracker = AuditTracker(db=db)

        # ── Recuperar o crear el Information State ────────────────────────────
        estado, turn_id = self._obtener_o_crear_estado(session_id, cliente_id)
        estado.turn_id = turn_id

        # ═══════════════════════════════════════════════════════════════════════
        # PASO 1: EXTRACT_NLU
        # Mistral analiza el mensaje y extrae entidades financieras estructuradas
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[Paso 1] EXTRACT_NLU — sesión=%s turno=%d", session_id[:8], turn_id)

        step1_input = {"mensaje": mensaje}
        nlu_resultado = self._mistral.extraer_nlu(mensaje)
        step1_output = nlu_resultado.model_dump()

        # Fusionar datos NLU en el estado (acumulativo)
        estado = self._actualizar_datos_usuario(estado, nlu_resultado)

        tracker.registrar_paso(
            session_id=session_id,
            turn_id=turn_id,
            step_order=1,
            action_type="EXTRACT_NLU",
            step_input=step1_input,
            step_output=step1_output,
            information_state=estado.as_dict(),
        )

        # ═══════════════════════════════════════════════════════════════════════
        # PASO 2: FETCH_CORE_DATA
        # Solo en el primer turno: cargar datos bancarios core desde la BD.
        # En turnos sucesivos ya están en el estado, no se vuelven a consultar.
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[Paso 2] FETCH_CORE_DATA — sesión=%s turno=%d", session_id[:8], turn_id)

        if turn_id == 1:
            step2_input = {"cliente_id": cliente_id, "motivo": "Primer turno — carga inicial"}
            cliente: ClienteModel | None = (
                db.query(ClienteModel)
                .filter(ClienteModel.cliente_id == cliente_id)
                .first()
            )

            if cliente is None:
                raise ValueError(
                    f"Cliente con ID '{cliente_id}' no encontrado en la base de datos. "
                    f"Verifique que el script de inicialización SQL se ha ejecutado."
                )

            estado.datos_core_bancario = DatosCoreBancario(
                cliente_id=cliente.cliente_id,
                nombre=cliente.nombre,
                dni=cliente.dni,
                edad=cliente.edad,
                ingresos_netos_mensuales=cliente.ingresos_netos_mensuales,
                antiguedad_meses=cliente.antiguedad_meses,
                deuda_interna_banco_mensual=cliente.deuda_interna_banco_mensual,
                es_avalista=cliente.es_avalista,
                empresa_avalada_cif=cliente.empresa_avalada_cif,
            )
            step2_output = estado.datos_core_bancario.model_dump()
            logger.info(
                "[Paso 2] Cliente cargado: %s (%s, DNI=%s, edad=%d, ingresos=%.2f)",
                cliente.cliente_id,
                cliente.nombre,
                cliente.dni,
                cliente.edad,
                cliente.ingresos_netos_mensuales,
            )
        else:
            step2_input = {"cliente_id": cliente_id, "motivo": "Turno >1 — datos ya en estado"}
            step2_output = {"cached": True, "datos_core_bancario": estado.datos_core_bancario.model_dump()}
            logger.info(
                "[Paso 2] Datos core bancarios recuperados del estado cacheado (turno %d)",
                turn_id,
            )

        tracker.registrar_paso(
            session_id=session_id,
            turn_id=turn_id,
            step_order=2,
            action_type="FETCH_CORE_DATA",
            step_input=step2_input,
            step_output=step2_output,
            information_state=estado.as_dict(),
        )

        # ═══════════════════════════════════════════════════════════════════════
        # PASO 3: EVALUATE_PRELIMINARY
        # Drools evalúa con todos los datos disponibles hasta ahora.
        # Si hay datos de BdE de turnos anteriores, ya están en el estado.
        # ═══════════════════════════════════════════════════════════════════════
        logger.info(
            "[Paso 3] EVALUATE_PRELIMINARY — sesión=%s turno=%d",
            session_id[:8],
            turn_id,
        )

        step3_input = self._drools.construir_payload(estado.as_dict())
        drools_respuesta_preliminar = self._drools.evaluar_reglas(step3_input)
        step3_output = drools_respuesta_preliminar.model_dump()

        estado = self._actualizar_datos_drools(estado, drools_respuesta_preliminar)

        tracker.registrar_paso(
            session_id=session_id,
            turn_id=turn_id,
            step_order=3,
            action_type="EVALUATE_PRELIMINARY",
            step_input=step3_input,
            step_output=step3_output,
            information_state=estado.as_dict(),
        )

        # ═══════════════════════════════════════════════════════════════════════
        # PASO 4: FETCH_CIRBE_ASNEF (CONDICIONAL)
        # Solo se ejecuta si Drools devuelve REQUIERE_ACCION: CONSULTAR_CIRBE_ASNEF
        # Y los datos BdE no han sido consultados previamente en esta sesión.
        # ═══════════════════════════════════════════════════════════════════════
        necesita_cirbe = (
            drools_respuesta_preliminar.estado == "REQUIERE_ACCION"
            and drools_respuesta_preliminar.accion_requerida == "CONSULTAR_CIRBE_ASNEF"
            and not estado.datos_externos_bde.consultado
        )

        if necesita_cirbe:
            logger.info(
                "[Paso 4] FETCH_CIRBE_ASNEF — consultando BdE mock para DNI=%s",
                estado.datos_core_bancario.dni,
            )

            dni = estado.datos_core_bancario.dni
            step4_input = {
                "dni": dni,
                "motivo": "Drools solicitó CONSULTAR_CIRBE_ASNEF",
                "es_avalista": estado.datos_core_bancario.es_avalista,
            }

            datos_bde = self._bde.consultar_por_dni(dni)
            step4_output = datos_bde

            estado.datos_externos_bde = DatosExternosBde(
                consultado=datos_bde["consultado"],
                tiene_impagos_activos=datos_bde["tiene_impagos_activos"],
                importe_morosidad_asnef=datos_bde["importe_morosidad_asnef"],
                empresa_avalada_concurso=datos_bde.get("empresa_avalada_concurso"),
                deuda_cirbe_mensual=datos_bde["deuda_cirbe_mensual"],
                deuda_cirbe_total=datos_bde["deuda_cirbe_total"],
            )

            tracker.registrar_paso(
                session_id=session_id,
                turn_id=turn_id,
                step_order=4,
                action_type="FETCH_CIRBE_ASNEF",
                step_input=step4_input,
                step_output=step4_output,
                information_state=estado.as_dict(),
            )

            # ═══════════════════════════════════════════════════════════════════
            # PASO 5: EVALUATE_FINAL_DECISION (CONDICIONAL — solo después de CIRBE)
            # Drools reevalúa con los datos del BdE ya inyectados en el estado.
            # ═══════════════════════════════════════════════════════════════════
            logger.info(
                "[Paso 5] EVALUATE_FINAL_DECISION — reevaluando con datos BdE",
            )

            step5_input = self._drools.construir_payload(estado.as_dict())
            drools_respuesta_final = self._drools.evaluar_reglas(step5_input)
            step5_output = drools_respuesta_final.model_dump()

            estado = self._actualizar_datos_drools(estado, drools_respuesta_final)

            tracker.registrar_paso(
                session_id=session_id,
                turn_id=turn_id,
                step_order=5,
                action_type="EVALUATE_FINAL_DECISION",
                step_input=step5_input,
                step_output=step5_output,
                information_state=estado.as_dict(),
            )
        else:
            logger.info(
                "[Paso 4/5] Omitidos — FETCH_CIRBE_ASNEF no requerido "
                "(estado Drools: %s, ya consultado: %s)",
                drools_respuesta_preliminar.estado,
                estado.datos_externos_bde.consultado,
            )

        # ═══════════════════════════════════════════════════════════════════════
        # PASO 6: GENERATE_NATURAL_RESPONSE
        # Mistral recibe el information_state final en modo solo lectura y
        # genera la respuesta textual para el usuario.
        # ═══════════════════════════════════════════════════════════════════════
        logger.info(
            "[Paso 6] GENERATE_NATURAL_RESPONSE — estado final: %s",
            estado.evaluacion_drools.estado,
        )

        estado_final_dict = estado.as_dict()
        step6_input = {
            "information_state": estado_final_dict,
            "mensaje_usuario": mensaje,
            "modo": "READ_ONLY",
        }

        respuesta_texto = self._mistral.generar_nlg(
            state=estado_final_dict,
            mensaje_usuario=mensaje,
        )
        step6_output = {"respuesta": respuesta_texto}

        tracker.registrar_paso(
            session_id=session_id,
            turn_id=turn_id,
            step_order=6,
            action_type="GENERATE_NATURAL_RESPONSE",
            step_input=step6_input,
            step_output=step6_output,
            information_state=estado_final_dict,
        )

        # ── Persistir el estado actualizado en caché ──────────────────────────
        self._persistir_estado(session_id, estado)

        logger.info(
            "Pipeline completado — sesión=%s turno=%d estado=%s",
            session_id[:8],
            turn_id,
            estado.evaluacion_drools.estado,
        )

        return respuesta_texto, estado_final_dict
