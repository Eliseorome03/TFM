/**
 * app.js — Lógica del Frontend Neurosimbólico Bancario
 *
 * Arquitectura: Vanilla JS puro, sin frameworks.
 * Responsabilidades:
 *   - Gestión de session_id (UUID v4 por sesión/cliente)
 *   - Carga reactiva del selector de clientes (GET /api/clientes)
 *   - Actualización de la tarjeta de core bancario al cambiar de cliente
 *   - Pipeline de chat: envío (POST /api/chat) y renderizado de respuesta
 *   - Actualización reactiva del panel de auditoría (derecha):
 *       · Sección 1: Timeline de píldoras del pipeline del turno
 *       · Sección 2: Insights del motor (intención, estado, reglas, legal)
 *       · Sección 3: JSON formateado del information_state final
 */

'use strict';

/* =============================================================================
   UTILIDADES
   ============================================================================= */

/**
 * Genera un UUID v4 conforme al RFC 4122.
 * @returns {string} UUID formateado como xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
 */
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Formatea una fecha en HH:MM:SS local.
 * @returns {string}
 */
function ahora() {
  return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

/**
 * Aplica coloración sintáctica al JSON para mostrar en <pre><code>.
 * Escapa HTML antes de reemplazar para evitar XSS.
 * @param {*} obj — Objeto JS a formatear
 * @returns {string} HTML con clases de color
 */
function formatearJsonConColor(obj) {
  const json = JSON.stringify(obj, null, 2);
  // Escapar HTML primero
  const escaped = json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Aplicar colores sintácticos
  return escaped.replace(
    /("(?:[^"\\]|\\.)*")(\s*:)?|(\btrue\b|\bfalse\b)|\b(null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (match, key, colon, bool, nullVal, number) => {
      if (colon) {
        // Clave de objeto: eliminar comillas para comparar, pero devolver sin escapar
        return `<span class="json-key">${key}</span>${colon}`;
      }
      if (key) {
        // Valor string (entre comillas pero sin los dos puntos)
        return `<span class="json-string">${key}</span>`;
      }
      if (bool !== undefined) {
        return `<span class="json-boolean">${bool}</span>`;
      }
      if (nullVal !== undefined) {
        return `<span class="json-null">null</span>`;
      }
      if (number !== undefined) {
        return `<span class="json-number">${number}</span>`;
      }
      return match;
    }
  );
}

/**
 * Muestra un toast de notificación temporal.
 * @param {string} msg — Mensaje a mostrar
 * @param {'info'|'success'|'error'} tipo
 * @param {number} duracion — ms antes de ocultarse
 */
function mostrarToast(msg, tipo = 'info', duracion = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.className = 'visible';
  if (tipo === 'error')   toast.classList.add('toast--error');
  if (tipo === 'success') toast.classList.add('toast--success');

  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = '';
  }, duracion);
}

/** Escapa texto para insertarlo de forma segura en el DOM como HTML. */
function escapeHtml(str) {
  if (str == null) return '—';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* =============================================================================
   ESTADO DE LA APLICACIÓN
   ============================================================================= */

const Estado = {
  /** UUID de la sesión actual — se regenera al cambiar de cliente */
  sessionId: uuidv4(),

  /** Número de turno del cliente actual */
  turnId: 0,

  /** Objeto del cliente seleccionado actualmente */
  clienteActual: null,

  /** Lista completa de clientes cargados desde la API */
  clientes: [],

  /** Indica si hay una petición en curso (bloqueo de UI) */
  cargando: false,

  /** Information state del último turno completado */
  ultimoInformationState: null,
};

/* =============================================================================
   REFERENCIAS AL DOM
   ============================================================================= */

const DOM = {
  clienteSelect:     () => document.getElementById('clienteSelect'),
  coreCard:          () => document.getElementById('coreCard'),
  chatMessages:      () => document.getElementById('chatMessages'),
  chatInput:         () => document.getElementById('chatInput'),
  sendBtn:           () => document.getElementById('sendBtn'),
  turnCounter:       () => document.getElementById('turnCounter'),
  sessionIdDisplay:  () => document.getElementById('sessionIdDisplay'),
  consolePlaceholder:() => document.getElementById('consolePlaceholder'),
  consoleContent:    () => document.getElementById('consoleContent'),
  pipelineTimeline:  () => document.getElementById('pipelineTimeline'),
  pipelineTurnBadge: () => document.getElementById('pipelineTurnBadge'),
  intentionValue:    () => document.getElementById('intentionValue'),
  estadoValue:       () => document.getElementById('estadoValue'),
  reglasValue:       () => document.getElementById('reglasValue'),
  articuloValue:     () => document.getElementById('articuloValue'),
  textoLegalValue:   () => document.getElementById('textoLegalValue'),
  isuJson:           () => document.getElementById('isuJson'),
  isuTurnBadge:      () => document.getElementById('isuTurnBadge'),
  insightsTurnBadge: () => document.getElementById('insightsTurnBadge'),
};

/* =============================================================================
   SECCIÓN 1 — CARGA DE CLIENTES Y SELECTOR
   ============================================================================= */

/**
 * Llama a GET /api/clientes y puebla el <select id="clienteSelect">.
 * Al terminar, selecciona el primer cliente automáticamente.
 */
async function cargarClientes() {
  try {
    const response = await fetch('/api/clientes');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    Estado.clientes = data.clientes || [];

    const select = DOM.clienteSelect();
    select.innerHTML = '';

    if (Estado.clientes.length === 0) {
      select.innerHTML = '<option value="">— Sin clientes registrados —</option>';
      mostrarToast('⚠️ No hay clientes en la base de datos', 'error');
      return;
    }

    const escenariosPorId = {
      'CLI-001': '→ Aprobación',
      'CLI-002': '→ Riesgo aval',
      'CLI-003': '→ Morosidad ASNEF',
      'CLI-004': '→ Edad máxima',
    };

    Estado.clientes.forEach((cliente) => {
      const option = document.createElement('option');
      option.value = cliente.cliente_id;
      const nombre = cliente.nombre || cliente.cliente_id;
      const escenario = escenariosPorId[cliente.cliente_id] || '';
      option.textContent = `${cliente.cliente_id} — ${nombre} ${escenario}`;
      option.dataset.clienteJson = JSON.stringify(cliente);
      select.appendChild(option);
    });

    // Seleccionar el primero automáticamente
    if (Estado.clientes.length > 0) {
      seleccionarCliente(Estado.clientes[0]);
    }

    mostrarToast(`✓ ${Estado.clientes.length} clientes cargados`, 'success', 2000);

  } catch (err) {
    console.error('[cargarClientes]', err);
    mostrarToast('❌ Error cargando clientes: ' + err.message, 'error', 5000);
    DOM.clienteSelect().innerHTML = '<option value="">— Error de conexión —</option>';
  }
}

/* =============================================================================
   SECCIÓN 2 — TARJETA DE CORE BANCARIO
   ============================================================================= */

/**
 * Actualiza la tarjeta de resumen del cliente seleccionado.
 * Mapea los datos del endpoint GET /api/clientes al diseño de la tarjeta.
 * @param {Object} cliente — Objeto de cliente del listado de la API
 */
function actualizarTarjetaCore(cliente) {
  const card = DOM.coreCard();

  if (!cliente) {
    card.innerHTML = `<div class="core-card__empty">Selecciona un cliente para ver sus datos</div>`;
    return;
  }

  const nombre = cliente.nombre || cliente.cliente_id;
  const iniciales = nombre.split(' ').filter(Boolean).map(p => p[0]).slice(0, 2).join('').toUpperCase();

  // Calcular perfil de riesgo visual simplificado
  const ingresos = cliente.ingresos_netos_mensuales || 0;
  let perfilColor = 'accent';
  let perfilLabel = 'Solvente';
  if (ingresos < 1200)      { perfilLabel = 'Ingresos bajos';  }
  else if (ingresos < 2000) { perfilLabel = 'Ingresos medios'; }
  else                       { perfilLabel = 'Ingresos altos';  }

  const avalista = cliente.es_avalista
    ? `<div class="core-card__avalista-tag">⚠️ Avalista activo — CIF avalado</div>`
    : '';

  card.innerHTML = `
    <div class="core-card__header">
      <div>
        <div class="core-card__title">Core Bancario</div>
      </div>
      <div class="core-card__avatar">${escapeHtml(iniciales)}</div>
    </div>
    <div class="core-card__name">${escapeHtml(nombre)}</div>
    <div class="core-card__id">ID: ${escapeHtml(cliente.cliente_id)} · DNI: ${escapeHtml(cliente.dni)}</div>
    <div class="core-card__grid">
      <div class="core-card__metric">
        <div class="core-card__metric-label">💰 Ingresos netos/mes</div>
        <div class="core-card__metric-value ${perfilColor}">${ingresos.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</div>
      </div>
      <div class="core-card__metric">
        <div class="core-card__metric-label">🎂 Edad</div>
        <div class="core-card__metric-value">${escapeHtml(cliente.edad)} años</div>
      </div>
    </div>
    ${avalista}
  `;
}

/* =============================================================================
   SECCIÓN 3 — SELECCIÓN DE CLIENTE Y RESET DE SESIÓN
   ============================================================================= */

/**
 * Procesa la selección de un cliente:
 *   1. Actualiza Estado.clienteActual
 *   2. Regenera el session_id
 *   3. Actualiza la tarjeta core
 *   4. Limpia el chat y la consola de auditoría
 * @param {Object} cliente
 */
function seleccionarCliente(cliente) {
  Estado.clienteActual = cliente;
  Estado.sessionId = uuidv4();
  Estado.turnId = 0;
  Estado.ultimoInformationState = null;

  actualizarTarjetaCore(cliente);
  limpiarChat();
  limpiarConsola();

  // Actualizar el display del session_id en la consola
  const sessionDisplay = DOM.sessionIdDisplay();
  if (sessionDisplay) {
    sessionDisplay.textContent = Estado.sessionId.substring(0, 12) + '…';
  }

  // Actualizar contador de turno
  const turnCounter = DOM.turnCounter();
  if (turnCounter) {
    turnCounter.textContent = 'Turno 0';
  }
}

/* =============================================================================
   SECCIÓN 4 — CHAT
   ============================================================================= */

/**
 * Limpia el historial del chat y muestra el estado vacío inicial.
 */
function limpiarChat() {
  const container = DOM.chatMessages();
  container.innerHTML = `
    <div class="chat-empty" id="chatEmpty">
      <div class="chat-empty__icon">💬</div>
      <div class="chat-empty__title">Inicia la conversación</div>
      <div class="chat-empty__sub">Escribe tu mensaje para comenzar la evaluación del préstamo</div>
    </div>
  `;
}

/**
 * Añade un mensaje de burbuja al historial de chat.
 * @param {'user'|'bot'} rol
 * @param {string} texto — Texto plano del mensaje
 */
function añadirMensaje(rol, texto) {
  // Eliminar el estado vacío si existe
  const empty = document.getElementById('chatEmpty');
  if (empty) empty.remove();

  const container = DOM.chatMessages();
  const senderLabel = rol === 'user' ? 'Tú' : '🤖 Asesor IA';

  const div = document.createElement('div');
  div.className = `message message--${rol}`;
  div.innerHTML = `
    <div class="message__sender">${senderLabel}</div>
    <div class="message__bubble">${escapeHtml(texto)}</div>
    <div class="message__time">${ahora()}</div>
  `;

  container.appendChild(div);

  // Scroll al fondo
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });

  return div;
}

/**
 * Muestra el indicador "escribiendo..." (tres puntos animados).
 * @returns {HTMLElement} — El elemento para poder eliminarlo después
 */
function mostrarTyping() {
  const empty = document.getElementById('chatEmpty');
  if (empty) empty.remove();

  const container = DOM.chatMessages();
  const div = document.createElement('div');
  div.className = 'message message--bot message--typing';
  div.id = 'typingIndicator';
  div.innerHTML = `
    <div class="message__sender">🤖 Asesor IA</div>
    <div class="message__bubble">
      <div class="typing-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
  container.appendChild(div);

  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });

  return div;
}

/** Elimina el indicador de typing si existe. */
function ocultarTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

/* =============================================================================
   SECCIÓN 5 — CONSOLA DE AUDITORÍA (Panel derecho)
   ============================================================================= */

/**
 * Limpia la consola y muestra el placeholder inicial.
 */
function limpiarConsola() {
  DOM.consolePlaceholder().classList.remove('hidden');
  DOM.consoleContent().classList.add('hidden');
  DOM.pipelineTimeline().innerHTML = '';
  DOM.isuJson().innerHTML = '';
  DOM.isuJson().parentElement.innerHTML = '';
}

/**
 * Nombres amigables para los action_type del pipeline.
 */
const PIPELINE_LABELS = {
  EXTRACT_NLU:               { label: 'NLU',        icon: '🧠', title: 'Extracción NLU' },
  FETCH_CORE_DATA:           { label: 'CORE',       icon: '🏦', title: 'Datos Core' },
  EVALUATE_DROOLS:           { label: 'EVAL DROOLS',icon: '⚙️', title: 'Evaluación Motor' },
  FETCH_CIRBE_ASNEF:         { label: 'CIRBE',      icon: '🔍', title: 'Consulta BdE/ASNEF' },
  GENERATE_NATURAL_RESPONSE: { label: 'NLG',        icon: '✍️', title: 'Respuesta Natural' },
};

/**
 * Reconstruye el timeline de píldoras del pipeline del turno.
 * Los pasos se derivan del information_state y las trazas del último turno.
 * @param {string[]} actionTypes — Lista ordenada de action_type ejecutados
 * @param {number} turnId
 */
function renderizarPipeline(actionTypes, turnId) {
  const timeline = DOM.pipelineTimeline();
  const turnBadge = DOM.pipelineTurnBadge();

  if (turnBadge) turnBadge.textContent = `Turno ${turnId}`;

  timeline.innerHTML = '';

  actionTypes.forEach((tipo, idx) => {
    const meta = PIPELINE_LABELS[tipo] || { label: tipo, icon: '▶', title: tipo };

    // Conector → entre badges (excepto el primero)
    if (idx > 0) {
      const connector = document.createElement('span');
      connector.className = 'pipeline-connector';
      connector.textContent = '→';
      timeline.appendChild(connector);
    }

    const badgeEl = document.createElement('div');
    badgeEl.className = 'pipeline-badge';
    badgeEl.title = meta.title;
    badgeEl.innerHTML = `
      <div class="pipeline-badge__pill badge--${tipo}">
        <span>${meta.icon}</span>
        <span>${meta.label}</span>
      </div>
      <div class="pipeline-badge__step">Paso ${idx + 1}</div>
    `;
    timeline.appendChild(badgeEl);
  });
}

/**
 * Renderiza los Insights del Motor (Sección 2) a partir del information_state.
 * @param {Object} state — information_state completo del último turno
 * @param {number} turnId
 */
function renderizarInsights(state, turnId) {
  const insightsTurnBadge = DOM.insightsTurnBadge();
  if (insightsTurnBadge) insightsTurnBadge.textContent = `Turno ${turnId}`;

  // Extrae campos relevantes del ISU
  const intencion    = state?.datos_usuario?.intencion_principal || '—';
  const evalDrools   = state?.evaluacion_drools || {};
  const estadoDrools = evalDrools.estado || 'EN_PROCESO';
  const reglas       = evalDrools.reglas_disparadas || [];
  const articulo     = evalDrools.articulo_normativo || null;
  const textoLegal   = evalDrools.texto_legal || null;

  // Intención
  const intentionEl = DOM.intentionValue();
  if (intentionEl) {
    const iconMap = {
      SOLICITAR_PRESTAMO: '💳',
      CONSULTAR_DUDA:     '❓',
      SALUDAR:            '👋',
      OTRA:               '💬',
    };
    intentionEl.innerHTML = `${iconMap[intencion] || '▶'} <strong>${escapeHtml(intencion)}</strong>`;
  }

  // Estado Drools con badge coloreado
  const estadoEl = DOM.estadoValue();
  if (estadoEl) {
    estadoEl.innerHTML = `<span class="estado-badge estado--${escapeHtml(estadoDrools)}">${escapeHtml(estadoDrools)}</span>`;
  }

  // Reglas disparadas
  const reglasEl = DOM.reglasValue();
  if (reglasEl) {
    if (reglas.length === 0) {
      reglasEl.innerHTML = '<span style="color:var(--color-text-muted);font-size:11px">—</span>';
    } else {
      reglasEl.innerHTML = `<div class="reglas-list">${reglas.map(r => `<span class="regla-tag">${escapeHtml(r)}</span>`).join('')}</div>`;
    }
  }

  // Artículo normativo
  const articuloEl = DOM.articuloValue();
  if (articuloEl) {
    articuloEl.innerHTML = articulo
      ? `<span class="articulo-tag">${escapeHtml(articulo)}</span>`
      : '<span style="color:var(--color-text-muted);font-size:11px">—</span>';
  }

  // Texto legal
  const textoLegalEl = DOM.textoLegalValue();
  if (textoLegalEl) {
    textoLegalEl.innerHTML = textoLegal
      ? `<blockquote class="texto-legal">${escapeHtml(textoLegal)}</blockquote>`
      : '<span style="color:var(--color-text-muted);font-size:11px">—</span>';
  }
}

/**
 * Renderiza el snapshot ISU en el bloque scrollable <pre><code>.
 * @param {Object} state — information_state completo
 * @param {number} turnId
 */
function renderizarISU(state, turnId) {
  const isuTurnBadge = DOM.isuTurnBadge();
  if (isuTurnBadge) isuTurnBadge.textContent = `Turno ${turnId}`;

  // Re-inject the isu-body content since we need the element
  const isuSection = document.querySelector('.isu-body');
  if (!isuSection) return;

  isuSection.innerHTML = `<pre id="isuJson"><code>${formatearJsonConColor(state)}</code></pre>`;
}

/**
 * Actualiza la consola completa con los datos de la respuesta del chat.
 * Se llama tras recibir la respuesta de POST /api/chat.
 * @param {Object} responseData — ChatResponse devuelta por la API
 */
function actualizarConsola(responseData) {
  const { information_state, turn_id } = responseData;

  // Mostrar el contenido (ocultar placeholder)
  DOM.consolePlaceholder().classList.add('hidden');
  DOM.consoleContent().classList.remove('hidden');

  Estado.ultimoInformationState = information_state;

  // ── Derivar la lista de action_types ejecutados en este turno ───────────────
  // El pipeline ahora es dinámico y devuelve sus acciones exactas
  const actionTypes = responseData.acciones_ejecutadas || [];

  // ── Sección 1: Pipeline ─────────────────────────────────────────────────────
  renderizarPipeline(actionTypes, turn_id);

  // ── Sección 2: Insights ─────────────────────────────────────────────────────
  renderizarInsights(information_state, turn_id);

  // ── Sección 3: ISU JSON ─────────────────────────────────────────────────────
  renderizarISU(information_state, turn_id);

  // Actualizar contador de turno en la columna izquierda
  const turnCounter = DOM.turnCounter();
  if (turnCounter) {
    turnCounter.textContent = `Turno ${turn_id}`;
  }

  Estado.turnId = turn_id;
}

/* =============================================================================
   SECCIÓN 6 — ENVÍO DE MENSAJES (Función principal)
   ============================================================================= */

/**
 * Gestiona el envío del formulario de chat.
 * Realiza POST /api/chat con { mensaje, cliente_id, session_id }
 * y actualiza el chat y la consola de forma reactiva.
 */
async function enviarMensaje() {
  const inputEl = DOM.chatInput();
  const texto = inputEl.value.trim();

  // Validaciones de guardas
  if (!texto) return;
  if (Estado.cargando) return;

  if (!Estado.clienteActual) {
    mostrarToast('⚠️ Selecciona un cliente primero', 'error');
    return;
  }

  // Bloquear UI durante el procesamiento
  Estado.cargando = true;
  inputEl.disabled = true;
  DOM.sendBtn().disabled = true;
  inputEl.value = '';

  // Añadir mensaje del usuario al chat
  añadirMensaje('user', texto);

  // Mostrar indicador de typing
  mostrarTyping();

  try {
    const payload = {
      mensaje:    texto,
      cliente_id: Estado.clienteActual.cliente_id,
      session_id: Estado.sessionId,
    };

    const response = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const detail = errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(detail);
    }

    const data = await response.json();

    // Ocultar typing y mostrar respuesta del bot
    ocultarTyping();
    añadirMensaje('bot', data.respuesta);

    // Actualizar la consola de auditoría
    actualizarConsola(data);

    mostrarToast(`✓ Turno ${data.turn_id} completado — ${data.estado_evaluacion}`, 'success', 3000);

  } catch (err) {
    ocultarTyping();

    console.error('[enviarMensaje]', err);
    const errMsg = err.message || 'Error desconocido al contactar con el servidor.';
    añadirMensaje('bot', `⚠️ Error del sistema: ${errMsg}`);
    mostrarToast('❌ ' + errMsg, 'error', 5000);

  } finally {
    // Desbloquear UI
    Estado.cargando = false;
    inputEl.disabled = false;
    DOM.sendBtn().disabled = false;
    inputEl.focus();
  }
}

/* =============================================================================
   SECCIÓN 7 — EVENT LISTENERS
   ============================================================================= */

/**
 * Configura todos los event listeners de la aplicación.
 * Se llama una única vez al cargar el DOM.
 */
function inicializarEventListeners() {

  // ─ Selector de cliente: cambiar cliente resetea sesión ──────────────────────
  DOM.clienteSelect().addEventListener('change', (e) => {
    const clienteId = e.target.value;
    const cliente = Estado.clientes.find(c => c.cliente_id === clienteId);
    if (cliente) {
      seleccionarCliente(cliente);
      mostrarToast(`✓ Cliente cambiado a ${clienteId} — Nueva sesión iniciada`, 'success', 2500);
    }
  });

  // ─ Botón de envío ────────────────────────────────────────────────────────────
  DOM.sendBtn().addEventListener('click', enviarMensaje);

  // ─ Enter para enviar, Shift+Enter para nueva línea ──────────────────────────
  DOM.chatInput().addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviarMensaje();
    }
  });

  // ─ Auto-resize del textarea ─────────────────────────────────────────────────
  DOM.chatInput().addEventListener('input', () => {
    const el = DOM.chatInput();
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  });
}

/* =============================================================================
   SECCIÓN 8 — INICIALIZACIÓN DE LA APLICACIÓN
   ============================================================================= */

/**
 * Función de inicialización auto-ejecutada (IIFE).
 * Se ejecuta en DOMContentLoaded para garantizar que el DOM está disponible.
 */
(async function inicializarApp() {
  console.log('[NeurosimbólicoBancario] Inicializando aplicación…');
  console.log(`[NeurosimbólicoBancario] Session ID inicial: ${Estado.sessionId}`);

  // Inicializar el display de session_id
  const sessionDisplay = DOM.sessionIdDisplay();
  if (sessionDisplay) {
    sessionDisplay.textContent = Estado.sessionId.substring(0, 12) + '…';
    sessionDisplay.title = Estado.sessionId;
  }

  // Registrar listeners antes de cargar datos
  inicializarEventListeners();

  // Inicializar el chat vacío
  limpiarChat();

  // Cargar clientes desde la API (auto-selecciona el primero)
  await cargarClientes();

  console.log('[NeurosimbólicoBancario] Aplicación lista.');
})();
