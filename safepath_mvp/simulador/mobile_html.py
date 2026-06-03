"""SAFE-PATH - HTML de la vista móvil minimalista."""

MOBILE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="theme-color" content="#0f172a">
  <title>SafePath</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      height: 100%;
    }

    body {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100dvh;
      background: #0f172a;
      font-family: system-ui, -apple-system, sans-serif;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }

    #content {
      display: flex;
      justify-content: center;
      align-items: center;
    }

    button {
      width: min(80vw, 300px);
      padding: 1.4rem 2rem;
      font-size: clamp(1.1rem, 5vw, 1.4rem);
      border-radius: 14px;
      border: none;
      cursor: pointer;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.02em;
      transition: opacity 0.15s, transform 0.1s;
      -webkit-appearance: none;
    }

    button:active {
      opacity: 0.75;
      transform: scale(0.97);
    }

    #label {
      font-size: clamp(1.6rem, 7vw, 2.2rem);
      color: #334155;
      font-weight: 700;
      letter-spacing: 0.12em;
    }
  </style>
</head>
<body>
  <div id="content"><span id="label">safepath</span></div>

  <script>
    const content = document.getElementById('content');
    let lastEstado = null;

    function showButton(text, color, action) {
      if (content.dataset.mode === text) return;
      content.dataset.mode = text;
      content.innerHTML = '';
      const btn = document.createElement('button');
      btn.textContent = text;
      btn.style.background = color;
      btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.style.opacity = '0.6';
        try { await action(); } catch (_) {}
        setTimeout(() => { btn.disabled = false; btn.style.opacity = ''; }, 800);
      });
      content.appendChild(btn);
    }

    function showLabel() {
      if (content.dataset.mode === 'label') return;
      content.dataset.mode = 'label';
      content.innerHTML = '<span id="label">safepath</span>';
    }

    async function refresh() {
      try {
        const data = await fetch('/status').then(r => r.json());
        const estado = data.estado;
        if (estado === lastEstado) return;
        lastEstado = estado;

        if (estado === 'NORMAL') {
          showButton('Forzar alerta', '#ef4444', () => fetch('/trigger?estado=ALERTA'));
        } else if (estado === 'VERIFICANDO') {
          showButton('Cancelar alerta', '#22c55e', () => fetch('/cancel'));
        } else {
          showLabel();
        }
      } catch (_) {}
    }

    setInterval(refresh, 1000);
    refresh();
  </script>
</body>
</html>"""
