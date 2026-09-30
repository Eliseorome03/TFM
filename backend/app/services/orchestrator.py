"""
services/orchestrator.py — Orquestador del pipeline conversacional de 6 pasos.

Implementa la clase `PipelineOrchestrator` que ejecuta las 5 micro-acciones
secuenciales definidas en SYSTEM_SPEC.md 5, registrando cada una en el
ledger de auditoría mediante `AuditTracker`.

Pipeline por turno conversacional:
  1. EXTRACT_NLU         — Mistral extrae entidades del mensaje del usuario.
  2. FETCH_CORE_DATA     — FastAPI consulta la tabla 'clientes' (solo turno 1).
  4. FETCH_CIRBE_ASNEF   — (Condicional) BdE mock si Drools pide CONSULTAR_CIRBE_ASNEF.
  5. EVALUATE_DROOLS — (Condicional) Drools reevalúa con datos BdE.
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

class PipelineOrchestrator:
    """
    Orquestador del pipeline conversacional neurosimbólico.

    Ejecuta las 5 acciones secuenciales del ciclo por cada turno del usuario,
    manteniendo el InformationState mediante Rehidratación de Estado (Event Sourcing)
    leyendo la base de datos de auditoría, haciéndolo 100% Stateless.

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
        self, session_id: str, tracker: AuditTracker
    ) -> tuple[InformationState, int]:
        """
        Recupera el estado existente desde la BD (trazas) o crea uno nuevo para la sesión.

        Args:
            session_id: UUID de la sesión conversacional.
            tracker: Instancia de AuditTracker para leer la tabla.

        Returns:
            tuple: (InformationState, turn_id) con el estado y el número de turno.
        """
        estado_dict = tracker.obtener_ultimo_estado(session_id)
        if estado_dict:
            estado = InformationState.model_validate(estado_dict)
            estado.turn_id += 1
            turn_id = estado.turn_id
            logger.info(
                "Estado existente recuperado desde BD para sesión %s — Turno %d",
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

        # Mantener las reglas previas de este mismo turno
        reglas_acumuladas = estado.evaluacion_drools.reglas_disparadas.copy() if estado.evaluacion_drools else []
        reglas_acumuladas.extend(drools_response.reglas_disparadas)

        estado.evaluacion_drools = EvaluacionDrools(
            estado=EstadoEvaluacion(drools_response.estado),
            reglas_disparadas=reglas_acumuladas,
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
    ) -> tuple[str, dict, list[str]]:
        """
        Ejecuta el pipeline dinámico de 5 acciones para un turno conversacional.

        Método principal del orquestador. Ejecuta las acciones dinámicamente,
        registra cada una en la tabla de auditoría y devuelve la respuesta
        textual, el estado final del sistema y las acciones ejecutadas.

        Args:
            mensaje: Texto libre del mensaje del usuario.
            cliente_id: Identificador del cliente seleccionado.
            session_id: UUID de la sesión conversacional.
            db: Sesión SQLAlchemy para acceso a BD y auditoría.

        Returns:
            tuple: (respuesta_texto: str, information_state: dict, acciones_ejecutadas: list[str])
        """
        tracker = AuditTracker(db=db)

        # ── Recuperar o crear el Information State ────────────────────────────
        estado, turn_id = self._obtener_o_crear_estado(session_id, tracker)
        estado.turn_id = turn_id
        
        # Reseteamos las reglas disparadas al inicio del turno para que acumulen solo las iteraciones actuales
        if estado.evaluacion_drools:
            estado.evaluacion_drools.reglas_disparadas = []

        acciones_ejecutadas = []
        step_order = 1

        def registrar_accion(action_type: str, step_input: dict | str, step_output: dict | str):
            nonlocal step_order
            tracker.registrar_paso(
                session_id=session_id,
                turn_id=turn_id,
                step_order=step_order,
                action_type=action_type,
                step_input=step_input,
                step_output=step_output,
                information_state=estado.as_dict(),
            )
            acciones_ejecutadas.append(action_type)
            step_order += 1

        # ── Construir historial de contexto para Mistral NLU ──────────────────
        trazas = tracker.obtener_trazas_sesion(session_id)
        historico_mensajes = []
        for t in trazas:
            if t.action_type == "EXTRACT_NLU" and isinstance(t.step_input, dict) and "mensaje" in t.step_input:
                historico_mensajes.append(f"Usuario: {t.step_input['mensaje']}")
            elif t.action_type == "GENERATE_NATURAL_RESPONSE" and isinstance(t.step_output, dict) and "respuesta" in t.step_output:
                historico_mensajes.append(f"Sistema: {t.step_output['respuesta']}")
                
        historial_str = "\n".join(historico_mensajes[-4:]) if historico_mensajes else ""

        # ═══════════════════════════════════════════════════════════════════════
        # ACCIÓN 1: EXTRACT_NLU
        # Mistral analiza el mensaje y extrae entidades financieras estructuradas
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("[Acción] EXTRACT_NLU — sesión=%s turno=%d", session_id[:8], turn_id)

        step1_input = {"mensaje": mensaje, "contexto": historial_str}
        nlu_resultado = self._mistral.extraer_nlu(mensaje, historial=historial_str)
        step1_output = nlu_resultado.model_dump()

        # Fusionar datos NLU en el estado (acumulativo)
        estado = self._actualizar_datos_usuario(estado, nlu_resultado)

        registrar_accion("EXTRACT_NLU", step1_input, step1_output)

        # ═══════════════════════════════════════════════════════════════════════
        # ACCIÓN 2: FETCH_CORE_DATA
        # Solo en el primer turno: cargar datos bancarios core desde la BD.
        # En turnos sucesivos ya están en el estado, no se vuelven a consultar.
        # ═══════════════════════════════════════════════════════════════════════
        if turn_id == 1:
            logger.info("[Acción] FETCH_CORE_DATA — sesión=%s turno=%d", session_id[:8], turn_id)
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
                "Cliente cargado: %s (%s, DNI=%s, edad=%d, ingresos=%.2f)",
                cliente.cliente_id,
                cliente.nombre,
                cliente.dni,
                cliente.edad,
                cliente.ingresos_netos_mensuales,
            )
            registrar_accion("FETCH_CORE_DATA", step2_input, step2_output)
        else:
            logger.info(
                "FETCH_CORE_DATA omitido — Datos core bancarios recuperados del estado cacheado (turno %d)",
                turn_id,
            )

        # ═══════════════════════════════════════════════════════════════════════
        # BUCLE DINÁMICO: EVALUATE_DROOLS <-> FETCH_CIRBE_ASNEF
        # ═══════════════════════════════════════════════════════════════════════
        max_ciclos = 3
        ciclos = 0

        while ciclos < max_ciclos:
            ciclos += 1
            # ── EVALUATE_DROOLS ───────────────────────────────────────────────
            logger.info(
                "[Acción] EVALUATE_DROOLS (Ciclo %d) — sesión=%s turno=%d",
                ciclos,
                session_id[:8],
                turn_id,
            )
            drools_input = self._drools.construir_payload(estado.as_dict())
            drools_resp = self._drools.evaluar_reglas(drools_input)
            estado = self._actualizar_datos_drools(estado, drools_resp)
            registrar_accion("EVALUATE_DROOLS", drools_input, drools_resp.model_dump())

            necesita_cirbe = (
                drools_resp.estado == "REQUIERE_ACCION"
                and drools_resp.accion_requerida == "CONSULTAR_CIRBE_ASNEF"
            )

            if necesita_cirbe:
                if not estado.datos_externos_bde.consultado:
                    # ── FETCH_CIRBE_ASNEF ─────────────────────────────────────────
                    logger.info(
                        "[Acción] FETCH_CIRBE_ASNEF — consultando BdE mock para DNI=%s",
                        estado.datos_core_bancario.dni,
                    )
                    dni = estado.datos_core_bancario.dni
                    bde_input = {
                        "dni": dni,
                        "motivo": "Drools solicitó CONSULTAR_CIRBE_ASNEF",
                        "es_avalista": estado.datos_core_bancario.es_avalista,
                    }
                    bde_output = self._bde.consultar_por_dni(dni)

                    estado.datos_externos_bde = DatosExternosBde(
                        consultado=bde_output["consultado"],
                        tiene_impagos_activos=bde_output["tiene_impagos_activos"],
                        importe_morosidad_asnef=bde_output["importe_morosidad_asnef"],
                        empresa_avalada_concurso=bde_output.get("empresa_avalada_concurso"),
                        deuda_cirbe_mensual=bde_output["deuda_cirbe_mensual"],
                        deuda_cirbe_total=bde_output["deuda_cirbe_total"],
                    )
                    registrar_accion("FETCH_CIRBE_ASNEF", bde_input, bde_output)
                    # El bucle continúa para que Drools re-evalúe
                    continue
                else:
                    logger.error("Drools sigue solicitando CIRBE aunque ya fue consultado.")
                    break
            else:
                # No se requiere más información de fuentes externas
                break

        # ═══════════════════════════════════════════════════════════════════════
        # ACCIÓN 5: GENERATE_NATURAL_RESPONSE
        # Mistral recibe el information_state final en modo solo lectura y
        # genera la respuesta textual para el usuario.
        # ═══════════════════════════════════════════════════════════════════════
        logger.info(
            "[Acción] GENERATE_NATURAL_RESPONSE — estado final: %s",
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

        registrar_accion("GENERATE_NATURAL_RESPONSE", step6_input, step6_output)

        logger.info(
            "Pipeline completado — sesión=%s turno=%d estado=%s",
            session_id[:8],
            turn_id,
            estado.evaluacion_drools.estado,
        )

        return respuesta_texto, estado_final_dict, acciones_ejecutadas
