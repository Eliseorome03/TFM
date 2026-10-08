'use strict';

// -----------------------------------------------------------------------------
// UTILIDADES
// -----------------------------------------------------------------------------

function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function ahora() {
  return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function mostrarToast(msg, tipo = 'info', duracion = 3000) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = 'visible';
  if (tipo === 'error')   toast.classList.add('toast--error');
  if (tipo === 'success') toast.classList.add('toast--success');

  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.className = '';
  }, duracion);
}

function escapeHtml(str) {
  if (str == null) return '—';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatMessage(str) {
  if (str == null) return '—';
  let formatted = escapeHtml(str);
  
  // Convertir **texto** a <strong>texto</strong>
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Convertir *texto* a <em>texto</em>
  formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Convertir \n a <br>
  formatted = formatted.replace(/\n/g, '<br>');
  
  return formatted;
}

const formatoEur = v => v.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
const formatoPct = v => v.toFixed(2) + '%';

// -----------------------------------------------------------------------------
// ESTADO
// -----------------------------------------------------------------------------

const Estado = {
  sessionId: uuidv4(),
  turnId: 0,
  clienteActual: null,
  clientes: [],
  cargando: false,
};

// -----------------------------------------------------------------------------
// UI: INICIALIZACIÓN
// -----------------------------------------------------------------------------

function inicializarEventListeners() {
  // Resizer
  const resizer = document.getElementById('resizer');
  const container = document.getElementById('mainContainer');
  let isResizing = false;

  if (resizer && container) {
    resizer.addEventListener('mousedown', () => {
      isResizing = true;
      resizer.classList.add('active');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
      if (!isResizing) return;
      const newLeftWidth = Math.max(300, Math.min(e.clientX, window.innerWidth - 300));
      container.style.gridTemplateColumns = `${newLeftWidth}px 1fr`;
      resizer.style.left = `${newLeftWidth}px`;
    });

    document.addEventListener('mouseup', () => {
      if (isResizing) {
        isResizing = false;
        resizer.classList.remove('active');
        document.body.style.cursor = 'default';
        document.body.style.userSelect = 'auto';
      }
    });
  }

  // Accordions
  document.querySelectorAll('.accordion-header').forEach(header => {
    header.addEventListener('click', function () {
      this.parentElement.classList.toggle('open');
    });
  });

  // Select
  const clienteSelect = document.getElementById('clienteSelect');
  if (clienteSelect) {
    clienteSelect.addEventListener('change', (e) => {
      const clienteId = e.target.value;
      const cliente = Estado.clientes.find(c => c.cliente_id === clienteId);
      if (cliente) {
        seleccionarCliente(cliente);
        mostrarToast(`✓ Cliente cambiado a ${clienteId} — Nueva sesión iniciada`, 'success', 2500);
      }
    });
  }

  // Chat
  const sendBtn = document.getElementById('sendBtn');
  if (sendBtn) {
    sendBtn.addEventListener('click', enviarMensaje);
  }

  const chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        enviarMensaje();
      }
    });
  }
}

// -----------------------------------------------------------------------------
// LÓGICA DE NEGOCIO
// -----------------------------------------------------------------------------

async function cargarClientes() {
  try {
    const response = await fetch('/api/clientes');
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const data = await response.json();
    Estado.clientes = data.clientes || [];

    const select = document.getElementById('clienteSelect');
    if(select) select.innerHTML = '';

    if (Estado.clientes.length === 0) {
      if(select) select.innerHTML = '<option value="">— Sin clientes registrados —</option>';
      mostrarToast('⚠️ No hay clientes en la base de datos', 'error');
      return;
    }

    Estado.clientes.forEach((cliente) => {
      const option = document.createElement('option');
      option.value = cliente.cliente_id;
      const nombre = cliente.nombre || cliente.cliente_id;
      option.textContent = `${cliente.cliente_id} — ${nombre}`;
      if(select) select.appendChild(option);
    });

    if (Estado.clientes.length > 0) {
      seleccionarCliente(Estado.clientes[0]);
    }
  } catch (err) {
    console.error(err);
    mostrarToast('Error cargando clientes', 'error');
  }
}

function seleccionarCliente(cliente) {
  Estado.clienteActual = cliente;
  Estado.sessionId = uuidv4();
  Estado.turnId = 0;

  // Actualizar Tarjeta Core
  const nombre = cliente.nombre || cliente.cliente_id;
  const iniciales = nombre.split(' ').filter(Boolean).map(p => p[0]).slice(0, 2).join('').toUpperCase();
  const ingresos = cliente.ingresos_netos_mensuales || 0;

  const elCH = document.getElementById('coreCardHeader'); 
  if(elCH) elCH.style.display = 'block';
  
  const elCS = document.getElementById('coreCardStats'); 
  if(elCS) elCS.style.display = 'grid';

  const coreAvatar_el = document.getElementById('coreAvatar'); 
  if(coreAvatar_el) coreAvatar_el.textContent = iniciales;
  
  const coreName_el = document.getElementById('coreName'); 
  if(coreName_el) coreName_el.textContent = nombre;
  
  const coreIdAge_el = document.getElementById('coreIdAge'); 
  if(coreIdAge_el) coreIdAge_el.textContent = `${cliente.cliente_id} • ${cliente.edad} años`;
  
  const coreIncome_el = document.getElementById('coreIncome'); 
  if(coreIncome_el) coreIncome_el.textContent = formatoEur(ingresos);
  
  const coreAge_el = document.getElementById('coreAge'); 
  if(coreAge_el) coreAge_el.textContent = `${cliente.edad} años`;

  const sessionIdDisplay_el = document.getElementById('sessionIdDisplay'); 
  if(sessionIdDisplay_el) sessionIdDisplay_el.textContent = Estado.sessionId.substring(0, 12) + '...';
  
  const turnCounter_el = document.getElementById('turnCounter'); 
  if(turnCounter_el) turnCounter_el.textContent = 'Turno 0';

  limpiarChat();
  limpiarConsola();
}

function limpiarChat() {
  const container = document.getElementById('chatMessages');
  if(container) container.innerHTML = '';
}

function añadirMensaje(rol, texto) {
  const container = document.getElementById('chatMessages');
  if(!container) return;
  const div = document.createElement('div');
  div.className = `message ${rol}`;
  
  if (rol === 'assistant') {
      div.innerHTML = `
        <div class="message-content">${formatMessage(texto)}</div>
        <div class="message-time">${ahora()}</div>
      `;
  } else {
      div.innerHTML = `
        <div class="message-content">${formatMessage(texto)}</div>
        <div class="message-time">${ahora()}</div>
      `;
  }

  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function mostrarTyping() {
  const container = document.getElementById('chatMessages');
  if(!container) return;
  const div = document.createElement('div');
  div.className = 'message assistant typing-indicator';
  div.id = 'typingIndicator';
  div.innerHTML = `
    <div class="message-content" style="display: flex; gap: 4px; align-items: center; justify-content: center; height: 24px;">
      <div style="width: 6px; height: 6px; background: var(--text-tertiary); border-radius: 50%; animation: pulse 1s infinite;"></div>
      <div style="width: 6px; height: 6px; background: var(--text-tertiary); border-radius: 50%; animation: pulse 1s infinite 0.2s;"></div>
      <div style="width: 6px; height: 6px; background: var(--text-tertiary); border-radius: 50%; animation: pulse 1s infinite 0.4s;"></div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function ocultarTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function limpiarConsola() {
  const cCont = document.getElementById('consoleContent'); 
  if(cCont) cCont.style.display = 'none';
  const cPh = document.getElementById('consolePlaceholder'); 
  if(cPh) cPh.style.display = 'flex';
}

function actualizarConsola(responseData) {
  const { information_state, turn_id, acciones_ejecutadas } = responseData;

  const cPh2 = document.getElementById('consolePlaceholder'); 
  if(cPh2) cPh2.style.display = 'none';
  const cCont2 = document.getElementById('consoleContent'); 
  if(cCont2) cCont2.style.display = 'block';

  const turnCounter_el = document.getElementById('turnCounter'); 
  if(turnCounter_el) turnCounter_el.textContent = `Turno ${turn_id}`;
  
  const pipelineTurnBadge_el = document.getElementById('pipelineTurnBadge'); 
  if(pipelineTurnBadge_el) pipelineTurnBadge_el.textContent = turn_id;

  // Pipeline
  const timeline = document.getElementById('pipelineTimeline');
  if(timeline) {
    timeline.innerHTML = '';
    const lblMap = {
      EXTRACT_NLU: '1. NLU',
      FETCH_CORE_DATA: '2. CORE DATA',
      EVALUATE_DROOLS: '3. DROOLS',
      FETCH_CIRBE_ASNEF: '4. CIRBE',
      GENERATE_NATURAL_RESPONSE: '5. NLG'
    };

    (acciones_ejecutadas || []).forEach((tipo, idx) => {
      if (idx > 0) {
        const arrow = document.createElement('div');
        arrow.style.color = 'var(--text-tertiary)';
        arrow.style.fontWeight = '700';
        arrow.textContent = '→';
        timeline.appendChild(arrow);
      }
      const step = document.createElement('div');
      step.className = 'pipeline-step done';
      step.innerHTML = `<span>${lblMap[tipo] || tipo}</span><div class="pipeline-dot"></div>`;
      timeline.appendChild(step);
    });
  }

  // Insights DROOLS
  const evalDrools = information_state?.evaluacion_drools || {};
  const estadoDrools = evalDrools.estado || 'EN_PROCESO';
  const datoFaltante = evalDrools.dato_faltante || null;
  const reglas = evalDrools.reglas_disparadas || [];
  const articulo = evalDrools.articulo_normativo || null;
  const textoLegal = evalDrools.texto_legal || null;

  const estadoEl = document.getElementById('estadoValue');
  if (estadoEl) {
    let tagCls = 'tag';
    if (estadoDrools === 'APROBADO') tagCls += ' success';
    else if (estadoDrools === 'DENEGADO') tagCls += ' warning';
    else if (estadoDrools === 'REQUIERE_DATOS') tagCls += ' warning';
    else tagCls += ' accent';
    estadoEl.innerHTML = `<span class="${tagCls}">${escapeHtml(estadoDrools)}</span>`;
  }



  const reglasEl = document.getElementById('reglasValue');
  if (reglasEl) {
    if (reglas.length === 0) {
      reglasEl.innerHTML = '<span style="color:var(--text-tertiary)">—</span>';
    } else {
      reglasEl.innerHTML = `<div class="rules-list">${reglas.map(r => `<div class="rule-badge">${escapeHtml(r)}</div>`).join('')}</div>`;
    }
  }

  const articuloValue_el = document.getElementById('articuloValue'); 
  if(articuloValue_el) articuloValue_el.textContent = articulo || '—';

  const legalBoxContainer = document.getElementById('legalBoxContainer');
  if (legalBoxContainer) {
    if (textoLegal) {
      legalBoxContainer.style.display = 'block';
      const textoLegalValue_el = document.getElementById('textoLegalValue'); 
      if(textoLegalValue_el) textoLegalValue_el.textContent = textoLegal;
    } else {
      legalBoxContainer.style.display = 'none';
    }
  }

  // ISU
  const fmtEur = v => v != null ? formatoEur(v) : null;
  const fmtPct = v => v != null ? formatoPct(v) : null;
  const fmtMeses = v => v != null ? v + ' meses' : null;
  const fmtAnios = v => v != null ? v + ' años' : null;

  const kpiCantidad_el = document.getElementById('kpiCantidad'); 
  if(kpiCantidad_el) kpiCantidad_el.textContent = information_state?.datos_usuario?.cantidad_solicitada ? formatoEur(information_state.datos_usuario.cantidad_solicitada) : '—';
  
  const kpiPlazo_el = document.getElementById('kpiPlazo'); 
  if(kpiPlazo_el) kpiPlazo_el.textContent = information_state?.datos_usuario?.plazo_meses ? `${information_state.datos_usuario.plazo_meses} meses` : '—';
  
  const kpiCirbe_el = document.getElementById('kpiCirbe'); 
  if(kpiCirbe_el) kpiCirbe_el.textContent = information_state?.datos_externos_bde?.consultado ? '✅' : '⏳';

  const asig = (id, val) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = 'accordion-value';
    if (val === null || val === undefined) {
      el.textContent = '—';
      el.classList.add('null');
      return;
    }
    if (typeof val === 'boolean') {
      el.textContent = val ? 'Sí' : 'No';
      el.classList.add(val ? 'true' : 'false');
      return;
    }
    el.textContent = val;
  };

  const du = information_state?.datos_usuario || {};
  asig('accIntencion', du.intencion_principal);
  asig('accCantidad', fmtEur(du.cantidad_solicitada));
  asig('accPlazo', fmtMeses(du.plazo_meses));
  asig('accProposito', du.proposito);
  asig('accGastos', fmtEur(du.gastos_fijos_mensuales));
  asig('accDeudaDecl', fmtEur(du.deuda_declarada));

  const cb = information_state?.datos_core_bancario || {};
  asig('accClienteId', cb.cliente_id);
  asig('accNombre', cb.nombre);
  asig('accDni', cb.dni);
  asig('accEdad', fmtAnios(cb.edad));
  asig('accIngresos', fmtEur(cb.ingresos_netos_mensuales));
  asig('accAntiguedad', fmtMeses(cb.antiguedad_meses));
  asig('accDeudaBanco', fmtEur(cb.deuda_interna_banco_mensual));
  asig('accAvalista', cb.es_avalista);

  const bde = information_state?.datos_externos_bde || {};
  asig('accBdeConsultado', bde.consultado);
  asig('accBdeImpagos', bde.tiene_impagos_activos);
  asig('accBdeAsnef', fmtEur(bde.importe_morosidad_asnef));
  asig('accBdeCirbeMes', fmtEur(bde.deuda_cirbe_mensual));
  asig('accBdeCirbeTotal', fmtEur(bde.deuda_cirbe_total));

  const calc = information_state?.calculos_derivados || {};
  asig('accCalcCuota', fmtEur(calc.cuota_estimada));
  asig('accCalcRatio', fmtPct(calc.ratio_endeudamiento * 100)); // The ratio is 0.0104, so multiply by 100 for percentage
  asig('accCalcRemanente', fmtEur(calc.remanente_subsistencia));
  asig('accCalcEdadVenc', fmtAnios(calc.edad_al_vencimiento));
}

async function enviarMensaje() {
  const inputEl = document.getElementById('chatInput');
  if(!inputEl) return;
  const texto = inputEl.value.trim();

  if (!texto || Estado.cargando) return;
  if (!Estado.clienteActual) {
    mostrarToast('Selecciona un cliente primero', 'error');
    return;
  }

  Estado.cargando = true;
  inputEl.disabled = true;
  const sendBtn_el = document.getElementById('sendBtn'); 
  if(sendBtn_el) sendBtn_el.disabled = true;
  inputEl.value = '';

  añadirMensaje('user', texto);
  mostrarTyping();

  try {
    const payload = {
      mensaje: texto,
      cliente_id: Estado.clienteActual.cliente_id,
      session_id: Estado.sessionId,
    };

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error('Error en la comunicación con el backend');
    const data = await response.json();

    ocultarTyping();
    añadirMensaje('assistant', data.respuesta);
    actualizarConsola(data);

    mostrarToast(`Turno ${data.turn_id} completado`, 'success', 2000);
  } catch (err) {
    console.error(err);
    ocultarTyping();
    añadirMensaje('assistant', '⚠️ Error del sistema: No se pudo completar la solicitud.');
    mostrarToast('Error del sistema', 'error');
  } finally {
    Estado.cargando = false;
    inputEl.disabled = false;
    const sendBtn_el2 = document.getElementById('sendBtn'); 
    if(sendBtn_el2) sendBtn_el2.disabled = false;
    inputEl.focus();
  }
}

// -----------------------------------------------------------------------------
// INICIO
// -----------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', async () => {
  inicializarEventListeners();
  await cargarClientes();
});
