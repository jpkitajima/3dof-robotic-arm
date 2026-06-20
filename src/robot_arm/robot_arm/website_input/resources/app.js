const state = {
  lt: 0,
  rt: 0,
  buttons: {
    lb: false,
    rb: false,
    a: false,
    b: false,
    x: false,
    y: false,
    switch_on: false,
    switch_off: false,
    dpad_up: false,
    dpad_down: false,
    dpad_left: false,
    dpad_right: false,
  },
  sticks: {
    left: { x: 0, y: 0 },
    right: { x: 0, y: 0 },
  }
};

const els = {
  status: document.getElementById('status'),
  eeX: document.getElementById('eeX'),
  eeY: document.getElementById('eeY'),
  eeZ: document.getElementById('eeZ'),
  ppStart: document.getElementById('ppStart'),
  ppCapture: document.getElementById('ppCapture'),
  ppPoints: document.getElementById('ppPoints'),
  drawArt: document.getElementById('drawArt'),
  drawCircle: document.getElementById('drawCircle'),
  drawSvg: document.getElementById('drawSvg'),
  drawLine: document.getElementById('drawLine'),
  lt: document.getElementById('lt'),
  rt: document.getElementById('rt'),
  ltVal: document.getElementById('ltVal'),
  rtVal: document.getElementById('rtVal'),
  lsVal: document.getElementById('lsVal'),
  rsVal: document.getElementById('rsVal'),
  lsZone: document.getElementById('lsZone'),
  rsZone: document.getElementById('rsZone'),
  lsKnob: document.getElementById('lsKnob'),
  rsKnob: document.getElementById('rsKnob'),
  wsUrl: document.getElementById('wsUrl'),
  centerAll: document.getElementById('centerAll'),
};

const CARD_ORDER_STORAGE_KEY = 'robot-arm-card-order';

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

function slugify(text) {
  return String(text)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function safeStorageGet(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

function safeStorageSet(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (_) {
    // Ignore storage failures in constrained browsers.
  }
}

function buildCardHeader(card) {
  const title = card.querySelector('h2');
  if (!title) return;

  card.dataset.cardId = card.dataset.cardId || slugify(title.textContent) || 'card';

  if (title.parentElement && title.parentElement.classList.contains('card-header')) return;

  const header = document.createElement('div');
  header.className = 'card-header';

  const handle = document.createElement('button');
  handle.type = 'button';
  handle.className = 'card-drag-handle';
  handle.setAttribute('aria-label', `Reorder ${title.textContent}`);
  handle.textContent = 'Drag';

  card.insertBefore(header, title);
  header.appendChild(title);
  header.appendChild(handle);
}

function applyStoredCardOrder(layout) {
  const stored = safeStorageGet(CARD_ORDER_STORAGE_KEY);
  if (!stored) return;

  let order = null;
  try {
    order = JSON.parse(stored);
  } catch (_) {
    return;
  }

  if (!Array.isArray(order) || order.length === 0) return;

  const cardsById = new Map(
    Array.from(layout.querySelectorAll(':scope > .card')).map((card) => [card.dataset.cardId, card])
  );

  for (const cardId of order) {
    const card = cardsById.get(cardId);
    if (!card) continue;
    layout.appendChild(card);
    cardsById.delete(cardId);
  }

  for (const card of cardsById.values()) {
    layout.appendChild(card);
  }
}

function persistCardOrder(layout) {
  const order = Array.from(layout.querySelectorAll(':scope > .card')).map((card) => card.dataset.cardId);
  safeStorageSet(CARD_ORDER_STORAGE_KEY, JSON.stringify(order));
}

function findClosestCard(layout, draggingCard, pointerX, pointerY) {
  const cards = Array.from(layout.querySelectorAll(':scope > .card')).filter((card) => card !== draggingCard);
  let bestCard = null;
  let bestDistance = Number.POSITIVE_INFINITY;

  for (const card of cards) {
    const rect = card.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const dx = centerX - pointerX;
    const dy = centerY - pointerY;
    const distance = dx * dx + dy * dy;

    if (distance < bestDistance) {
      bestDistance = distance;
      bestCard = card;
    }
  }

  return bestCard;
}

function initCardReordering() {
  const layout = document.querySelector('.layout');
  if (!layout) return;

  const cards = Array.from(layout.querySelectorAll(':scope > .card'));
  for (const card of cards) {
    buildCardHeader(card);
  }

  applyStoredCardOrder(layout);

  let dragState = null;

  function finishDrag() {
    if (!dragState) return;

    const { card, handle, placeholder } = dragState;
    if (placeholder.parentElement) {
      placeholder.replaceWith(card);
    }

    card.classList.remove('card-dragging');
    handle.classList.remove('drag-active');
    card.style.left = '';
    card.style.top = '';
    card.style.width = '';
    card.style.height = '';

    persistCardOrder(layout);
    dragState = null;
  }

  function onPointerMove(ev) {
    if (!dragState || ev.pointerId !== dragState.pointerId) return;
    ev.preventDefault();

    const { card, placeholder, offsetX, offsetY } = dragState;
    card.style.left = `${ev.clientX - offsetX}px`;
    card.style.top = `${ev.clientY - offsetY}px`;

    const closestCard = findClosestCard(layout, card, ev.clientX, ev.clientY);
    if (!closestCard || closestCard === placeholder) return;

    const rect = closestCard.getBoundingClientRect();
    const isAfter = ev.clientY > rect.top + rect.height / 2
      || (
        Math.abs(ev.clientY - (rect.top + rect.height / 2)) < rect.height * 0.2
        && ev.clientX > rect.left + rect.width / 2
      );

    if (isAfter) {
      layout.insertBefore(placeholder, closestCard.nextSibling);
      return;
    }

    layout.insertBefore(placeholder, closestCard);
  }

  function onPointerUp(ev) {
    if (!dragState || ev.pointerId !== dragState.pointerId) return;
    ev.preventDefault();
    finishDrag();
  }

  for (const card of Array.from(layout.querySelectorAll(':scope > .card'))) {
    const handle = card.querySelector('.card-drag-handle');
    if (!handle) continue;

    handle.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();

      if (dragState) finishDrag();

      const rect = card.getBoundingClientRect();
      const placeholder = document.createElement('div');
      placeholder.className = 'card card-placeholder';
      placeholder.style.height = `${rect.height}px`;

      dragState = {
        card,
        handle,
        placeholder,
        pointerId: ev.pointerId,
        offsetX: ev.clientX - rect.left,
        offsetY: ev.clientY - rect.top,
      };

      card.classList.add('card-dragging');
      handle.classList.add('drag-active');
      card.style.width = `${rect.width}px`;
      card.style.height = `${rect.height}px`;
      card.style.left = `${rect.left}px`;
      card.style.top = `${rect.top}px`;

      layout.insertBefore(placeholder, card.nextSibling);
      handle.setPointerCapture(ev.pointerId);
    });
  }

  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerUp);
}

let pathProgrammerPoints = [];

function wsSend(obj) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(obj));
}

function renderPathPoints() {
  if (!els.ppPoints) return;
  els.ppPoints.innerHTML = '';

  for (let i = 0; i < pathProgrammerPoints.length; i++) {
    const p = pathProgrammerPoints[i];

    const li = document.createElement('li');
    li.className = 'point-row';

    const pill = document.createElement('span');
    pill.className = 'pill';
    pill.textContent = `x:${p.x.toFixed(3)} y:${p.y.toFixed(3)} z:${p.z.toFixed(3)}`;

    const btn = document.createElement('button');
    btn.className = 'btn danger';
    btn.textContent = 'x';
    btn.addEventListener('click', (ev) => {
      ev.preventDefault();
      wsSend({ type: 'path_programmer_remove_point', index: i });
    });

    li.appendChild(pill);
    li.appendChild(btn);
    els.ppPoints.appendChild(li);
  }
}

function setPressed(btnEl, pressed) {
  if (pressed) btnEl.classList.add('pressed');
  else btnEl.classList.remove('pressed');
}

function bindPressHoldButton(btnEl, key) {
  const press = (ev) => {
    ev.preventDefault();
    state.buttons[key] = true;
    setPressed(btnEl, true);
  };
  const release = (ev) => {
    ev.preventDefault();
    state.buttons[key] = false;
    setPressed(btnEl, false);
  };

  btnEl.addEventListener('pointerdown', press);
  btnEl.addEventListener('pointerup', release);
  btnEl.addEventListener('pointercancel', release);
  btnEl.addEventListener('pointerleave', release);
}

function bindActionButton(btnEl, actionType) {
  if (!btnEl) return;

  btnEl.addEventListener('click', (ev) => {
    ev.preventDefault();
    wsSend({ type: actionType });
  });
}

function updateTrigger(which) {
  const el = which === 'lt' ? els.lt : els.rt;
  const valEl = which === 'lt' ? els.ltVal : els.rtVal;
  const v = clamp(parseFloat(el.value), -1, 1);
  state[which] = v;
  valEl.textContent = v.toFixed(2);
}

els.lt.addEventListener('input', () => updateTrigger('lt'));
els.rt.addEventListener('input', () => updateTrigger('rt'));
updateTrigger('lt');
updateTrigger('rt');

document.querySelectorAll('[data-btn]').forEach((btn) => {
  bindPressHoldButton(btn, btn.getAttribute('data-btn'));
});

if (els.ppStart) {
  els.ppStart.addEventListener('click', (ev) => {
    ev.preventDefault();
    wsSend({ type: 'path_programmer_start' });
  });
}

if (els.ppCapture) {
  els.ppCapture.addEventListener('click', (ev) => {
    ev.preventDefault();
    wsSend({ type: 'path_programmer_capture_current_position' });
  });
}

bindActionButton(els.drawArt, 'start_drawing_art');
bindActionButton(els.drawCircle, 'start_drawing_circle');
bindActionButton(els.drawSvg, 'start_drawing_svg');
bindActionButton(els.drawLine, 'start_drawing_line');

function setupStick(zoneEl, knobEl, which) {
  const maxRadius = 0.40; // fraction of half-size
  let activePointerId = null;

  function setStick(x, y) {
    // x,y in [-1,1]
    x = clamp(x, -1, 1);
    y = clamp(y, -1, 1);
    state.sticks[which].x = x;
    state.sticks[which].y = y;

    const rect = zoneEl.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const radius = Math.min(cx, cy) * maxRadius;
    knobEl.style.left = (cx + x * radius - knobEl.offsetWidth / 2) + 'px';
    knobEl.style.top = (cy - y * radius - knobEl.offsetHeight / 2) + 'px';

    const text = `x:${x.toFixed(2)} y:${y.toFixed(2)}`;
    if (which === 'left') els.lsVal.textContent = text;
    else els.rsVal.textContent = text;
  }

  function center() { setStick(0, 0); }
  center();

  zoneEl.addEventListener('pointerdown', (ev) => {
    ev.preventDefault();
    activePointerId = ev.pointerId;
    zoneEl.setPointerCapture(activePointerId);
  });

  zoneEl.addEventListener('pointermove', (ev) => {
    if (activePointerId !== ev.pointerId) return;
    ev.preventDefault();

    const rect = zoneEl.getBoundingClientRect();
    const nx = (ev.clientX - (rect.left + rect.width / 2)) / (rect.width / 2);
    const ny = (ev.clientY - (rect.top + rect.height / 2)) / (rect.height / 2);

    // invert Y so up is +1 like typical joystick conventions
    setStick(nx, -ny);
  });

  const release = (ev) => {
    if (activePointerId !== ev.pointerId) return;
    ev.preventDefault();
    activePointerId = null;
    try { zoneEl.releasePointerCapture(ev.pointerId); } catch (_) {}
    center();
  };

  zoneEl.addEventListener('pointerup', release);
  zoneEl.addEventListener('pointercancel', release);
  zoneEl.addEventListener('pointerleave', release);

  return { center };
}

const ls = setupStick(els.lsZone, els.lsKnob, 'left');
const rs = setupStick(els.rsZone, els.rsKnob, 'right');

els.centerAll.addEventListener('click', () => {
  els.lt.value = '0';
  els.rt.value = '0';
  updateTrigger('lt');
  updateTrigger('rt');
  ls.center();
  rs.center();
});

// Websocket
let ws = null;
let lastSendTs = 0;

function wsAddress() {
  const proto = (window.location.protocol === 'https:') ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws`;
}

function setStatus(text) { els.status.textContent = text; }

function connect() {
  const url = wsAddress();
  els.wsUrl.textContent = url;

  ws = new WebSocket(url);

  ws.addEventListener('open', () => {
    setStatus('Connected');
  });

  ws.addEventListener('message', (ev) => {
    let payload = null;
    try {
      payload = JSON.parse(ev.data);
    } catch (_) {
      return;
    }

    if (!payload || typeof payload !== 'object') return;

    if (payload.type === 'cartesian_xyz_read') {
      const x = Number(payload.x);
      const y = Number(payload.y);
      const z = Number(payload.z);
      if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) return;

      if (els.eeX) els.eeX.textContent = x.toFixed(3);
      if (els.eeY) els.eeY.textContent = y.toFixed(3);
      if (els.eeZ) els.eeZ.textContent = z.toFixed(3);
      return;
    }

    if (payload.type === 'path_programmer_points') {
      const pts = Array.isArray(payload.points) ? payload.points : null;
      if (!pts) return;

      const parsed = [];
      for (const item of pts) {
        if (!item || typeof item !== 'object') continue;
        const x = Number(item.x);
        const y = Number(item.y);
        const z = Number(item.z);
        if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(z)) continue;
        parsed.push({ x, y, z });
      }

      pathProgrammerPoints = parsed;
      renderPathPoints();
      return;
    }
  });

  ws.addEventListener('close', () => {
    setStatus('Disconnected — retrying…');
    ws = null;
    setTimeout(connect, 600);
  });

  ws.addEventListener('error', () => {
    setStatus('WebSocket error — retrying…');
  });
}

function buildPayload() {
  return {
    type: 'state',
    ts_ms: Date.now(),
    lt: state.lt,
    rt: state.rt,
    buttons: { ...state.buttons },
    sticks: {
      left: { ...state.sticks.left },
      right: { ...state.sticks.right },
    },
  };
}

function trySend() {
  const now = Date.now();
  if (now - lastSendTs < 50) return; // 20Hz
  lastSendTs = now;

  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify(buildPayload()));
}

// send loop
setInterval(trySend, 20);
connect();
initCardReordering();
