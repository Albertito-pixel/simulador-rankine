import streamlit as st
import CoolProp.CoolProp as CP
import plotly.graph_objects as go
import numpy as np
import json
import matplotlib.patches as patches
import matplotlib.pyplot as plt

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILO INDUSTRIAL
# ==========================================
st.set_page_config(
    page_title="Thermodynamics Rankine | UTP",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded" 
)

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {
        background-color: #0b0f19;
        background-image: radial-gradient(circle at 50% 0%, #1a2235 0%, #0b0f19 70%);
    }
    .gradient-text {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 20px;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, border 0.3s ease;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(79, 172, 254, 0.3);
        box-shadow: 0 10px 40px rgba(0, 242, 254, 0.1);
    }
    .highlight-number {
        font-size: 2rem;
        color: #fff;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }
    .label-text {
        color: #8b9eb7;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    [data-testid="collapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 15px !important;
        left: 15px !important;
        z-index: 999999 !important;
        background-color: #0f172a !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 8px !important;
        padding: 8px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5) !important;
    }
    [data-testid="collapsedControl"] svg {
        fill: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; padding: 25px; margin-bottom: 25px; text-align: center;">
    <h1 style="color: #ffffff; font-size: 2.8rem; font-weight: 800; margin: 0; padding-bottom: 5px; font-family: 'Segoe UI', sans-serif;">Thermodynamics Rankine</h1>
    <p style="color: #94a3b8; font-size: 1.1rem; margin: 0 0 15px 0;">Simulador térmico integral: ciclos de potencia regenerativos con trampas/bombas, cogeneración y diagramas T-s dinámicos.</p>
    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">
        <span style="color: #38bdf8; font-weight: 600; font-size: 1.1rem;">Desarrollado por:</span> <span style="color: #cbd5e1; font-size: 1.1rem;">Alberto Mendieta | Cédula: 6-728-80 | UTP Azuero</span>
    </div>
</div>
""", unsafe_allow_html=True)

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np


def dibujar_diagrama_planta(
    p_cald_kpa,
    t_cald,
    p_cond_kpa,
    fwh_ord=None,
    tiene_recal=False,
    p_recal_kpa=None,
    t_recal=None,
    estados_ciclo=None,
    w_t_total=None,
    q_in_total=None,
    q_out_cond=None,
):
  if fwh_ord is None:
    fwh_ord = []
  if estados_ciclo is None:
    estados_ciclo = {}

  fig, ax = plt.subplots(figsize=(16.8, 8.8), dpi=130)
  ax.set_xlim(-0.5, 16.5)
  ax.set_ylim(-3.2, 9.2)
  ax.axis('off')

  box_style = dict(
      boxstyle='round,pad=0.35,rounding_size=0.25',
      facecolor='#edf2f7',
      edgecolor='#1a202c',
      linewidth=1.6,
  )
  txt_m = dict(
      ha='center',
      va='center',
      fontfamily='sans-serif',
      color='#0f172a',
      fontweight='bold',
  )
  txt_s = dict(
      ha='center', va='center', fontfamily='sans-serif', color='#475569'
  )

  def fmt_p(p_in):
    if p_in is None or p_in <= 0:
      return ''
    p_kpa = p_in / 1e3 if p_in > 50000 else p_in
    if p_kpa >= 1000:
      return f'{p_kpa/1e3:.2f} MPa'
    return f'{p_kpa:.1f} kPa'

  def fmt_pot(val_kw, prefijo='Q'):
    if val_kw is None or val_kw == 0:
      return ''
    if abs(val_kw) >= 10000:
      return f'{prefijo} = {val_kw/1e3:,.1f} MW'
    return f'{prefijo} = {val_kw:,.0f} kW'

  def get_p_t(num, p_def=None, t_def=None):
    if num in estados_ciclo:
      return estados_ciclo[num].get('P', p_def), estados_ciclo[num].get(
          'T', t_def
      )
    return p_def, t_def

  def etiqueta_estado(x, y, num, p_val=None, t_val=None, pos='top'):
    if num is None:
      return
    p_r, t_r = get_p_t(num, p_val, t_val)
    ax.scatter(
        [x],
        [y],
        s=440,
        facecolor='white',
        edgecolor='#0f172a',
        linewidth=1.6,
        zorder=8,
    )
    ax.text(
        x,
        y,
        str(num),
        fontweight='bold',
        fontsize=9.0,
        zorder=9,
        ha='center',
        va='center',
        color='#0f172a',
    )

    p_str = fmt_p(p_r)
    t_str = f'{t_r:.1f} °C' if t_r is not None else ''
    info = f'{p_str}\n{t_str}'.strip()
    if info:
      y_off = 0.52 if pos == 'top' else -0.52
      v_align = 'bottom' if pos == 'top' else 'top'
      ax.text(
          x,
          y + y_off,
          info,
          fontsize=7.3,
          ha='center',
          va=v_align,
          color='#1e293b',
          fontweight='bold',
          zorder=9,
      )

  # =======================================================
  # ASIGNACIÓN DE ESTADOS DINÁMICA BASADA EN ESTADOS_CICLO
  # =======================================================
  n_fwh = len(fwh_ord)
  max_st = max(estados_ciclo.keys()) if estados_ciclo else (15 if tiene_recal else 6)

  # En ciclos Rankine regenerativos:
  # 1: Salida Condensador, 2: Salida Bomba 1
  st_cond_out = 1
  st_b1_out = 2
  st_esc_cond = max_st

  # Entrada a turbina de alta y caldera
  if tiene_recal and n_fwh > 0:
    st_cald_in = 8 if 8 in estados_ciclo else (max_st - (n_fwh + 3))
    st_turb_in = 9 if 9 in estados_ciclo else (st_cald_in + 1)
    st_rec_in = 10 if 10 in estados_ciclo else (st_turb_in + 1)
    st_rec_out = 11 if 11 in estados_ciclo else (st_rec_in + 1)
  elif tiene_recal:
    st_cald_in = 2
    st_turb_in = 3
    st_rec_in = 4
    st_rec_out = 5
  else:
    st_cald_in = 2 + 2 * n_fwh if n_fwh > 0 else 2
    st_turb_in = st_cald_in + 1
    st_rec_in = None
    st_rec_out = None

  # =======================================================
  # 1. CALDERA Y CONDENSADOR
  # =======================================================
  caldera = patches.FancyBboxPatch(
      (0.3, 4.6), 2.3, 2.5, **box_style, zorder=3
  )
  ax.add_patch(caldera)
  ax.text(1.45, 6.4, 'Caldera', fontsize=10, **txt_m)
  q_lbl = fmt_pot(q_in_total, 'Q')
  if q_lbl:
    ax.text(1.45, 5.85, q_lbl, fontsize=7.8, **txt_s)
  sx = np.linspace(0.6, 2.3, 11)
  sy = [4.9 if i % 2 == 0 else 5.35 for i in range(11)]
  ax.plot(sx, sy, color='#dc2626', lw=2.0, zorder=4)

  cond = patches.FancyBboxPatch((13.0, 4.6), 2.3, 2.5, **box_style, zorder=3)
  ax.add_patch(cond)
  ax.text(14.15, 6.4, 'Condensador', fontsize=10, **txt_m)
  qc_lbl = fmt_pot(q_out_cond, 'Q')
  if qc_lbl:
    ax.text(14.15, 5.85, qc_lbl, fontsize=7.8, **txt_s)
  for cy in [4.9, 5.15, 5.4]:
    ax.plot([13.3, 15.0], [cy, cy], color='#0284c7', lw=1.4, zorder=4)

  # =======================================================
  # 2. TURBINAS Y RECALENTADOR
  # =======================================================
  y_turb = 5.7
  if tiene_recal:
    tap = patches.Polygon(
        [[3.8, 6.8], [5.7, 7.3], [5.7, 4.4], [3.8, 4.9]],
        facecolor='#edf2f7',
        edgecolor='#1a202c',
        lw=1.6,
        zorder=3,
    )
    ax.add_patch(tap)
    ax.text(4.75, 6.0, 'Turbina\nde alta', fontsize=8.5, **txt_m)

    recal = patches.FancyBboxPatch(
        (6.7, 4.7), 1.9, 2.3, **box_style, zorder=3
    )
    ax.add_patch(recal)
    ax.text(7.65, 6.4, 'Recalentador', fontsize=8.5, **txt_m)
    rx = np.linspace(7.0, 8.3, 9)
    ry = [5.0 if i % 2 == 0 else 5.45 for i in range(9)]
    ax.plot(rx, ry, color='#dc2626', lw=1.8, zorder=4)

    tbp = patches.Polygon(
        [[9.5, 6.8], [11.9, 7.5], [11.9, 4.2], [9.5, 4.9]],
        facecolor='#edf2f7',
        edgecolor='#1a202c',
        lw=1.6,
        zorder=3,
    )
    ax.add_patch(tbp)
    ax.text(10.7, 6.0, 'Turbina\nde baja', fontsize=8.5, **txt_m)

    ax.annotate(
        '',
        xy=(3.8, y_turb),
        xytext=(2.6, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#b91c1c', lw=3.0),
    )
    etiqueta_estado(3.2, y_turb, st_turb_in, p_cald_kpa, t_cald, pos='top')

    ax.annotate(
        '',
        xy=(6.7, y_turb),
        xytext=(5.7, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#b91c1c', lw=2.5),
    )
    etiqueta_estado(6.2, y_turb, st_rec_in, p_recal_kpa, None, pos='top')

    ax.annotate(
        '',
        xy=(9.5, y_turb),
        xytext=(8.6, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#b91c1c', lw=2.5),
    )
    etiqueta_estado(9.05, y_turb, st_rec_out, p_recal_kpa, t_recal, pos='top')

    ax.annotate(
        '',
        xy=(13.0, y_turb),
        xytext=(11.9, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#0284c7', lw=2.5),
    )
    etiqueta_estado(12.45, y_turb, st_esc_cond, p_cond_kpa, None, pos='top')
  else:
    tu = patches.Polygon(
        [[4.2, 7.1], [11.5, 7.9], [11.5, 3.9], [4.2, 4.7]],
        facecolor='#edf2f7',
        edgecolor='#1a202c',
        lw=1.6,
        zorder=3,
    )
    ax.add_patch(tu)
    ax.text(7.6, 6.2, 'Turbina de Vapor', fontsize=10.5, **txt_m)

    ax.annotate(
        '',
        xy=(4.2, y_turb),
        xytext=(2.6, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#b91c1c', lw=3.0),
    )
    etiqueta_estado(3.4, y_turb, st_turb_in, p_cald_kpa, t_cald, pos='top')

    ax.annotate(
        '',
        xy=(13.0, y_turb),
        xytext=(11.5, y_turb),
        arrowprops=dict(arrowstyle='-|>', color='#0284c7', lw=2.5),
    )
    etiqueta_estado(12.25, y_turb, st_esc_cond, p_cond_kpa, None, pos='top')

  # =======================================================
  # 3. TREN DE AGUA INFERIOR (ESPACIADO VERTICAL MEJORADO)
  # =======================================================
  y_feed = 0.5  # Bajado a 0.5 para dar holgura a las etiquetas superiores
  y_drain = -1.9  # Línea de drenajes bien abajo

  # Bomba 1
  b1 = patches.Circle(
      (12.3, y_feed),
      0.45,
      facecolor='#edf2f7',
      edgecolor='#1a202c',
      lw=1.6,
      zorder=5,
  )
  ax.add_patch(b1)
  ax.text(12.3, y_feed, 'Bomba 1', fontsize=7.6, zorder=6, **txt_m)

  # Tubo Condensador -> Bomba 1
  ax.plot(
      [14.15, 14.15, 12.3, 12.3],
      [4.6, 2.3, 2.3, y_feed + 0.45],
      color='#0369a1',
      lw=3.0,
      zorder=2,
  )
  ax.annotate(
      '',
      xy=(12.3, y_feed + 0.45),
      xytext=(12.3, 1.6),
      arrowprops=dict(arrowstyle='-|>', color='#0369a1', lw=3.0),
  )
  etiqueta_estado(13.2, 2.3, st_cond_out, p_cond_kpa, None, pos='top')

  # Entrada a Caldera (Estado 8)
  ax.plot([1.45, 1.45], [y_feed, 4.6], color='#0369a1', lw=3.0, zorder=2)
  ax.annotate(
      '',
      xy=(1.45, 4.6),
      xytext=(1.45, 3.5),
      arrowprops=dict(arrowstyle='-|>', color='#0369a1', lw=3.0),
  )
  etiqueta_estado(1.45, 2.6, st_cald_in, p_cald_kpa, None, pos='top')

  if n_fwh > 0:
    xs = np.linspace(4.2, 10.3, n_fwh)
    w_box = max(1.3, min(1.8, 5.0 / n_fwh))
    h_box = 1.4

    # Tubo de agua continuo
    ax.plot([11.85, 1.45], [y_feed, y_feed], color='#0369a1', lw=3.0, zorder=2)
    etiqueta_estado(11.3, y_feed, st_b1_out, pos='top')

    # Estado 6: Salida de agua del Calentador Cerrado 1 hacia la caldera
    st_sal_fwh1 = 6 if 6 in estados_ciclo else (st_cald_in - 2)
    etiqueta_estado(2.7, y_feed, st_sal_fwh1, pos='top')
    
    for i, f in enumerate(fwh_ord):
      xc = xs[i]
      p_raw = f.get('presion', f.get('P', 0))
      y_val = f.get('y', 0.0)
      drenaje = f.get('drenaje', '')
      es_abierto = 'Abierto' in f.get('tipo', 'Cerrado')
      tiene_trampa = 'Trampa' in drenaje

      # Caja del Calentador
      fwh_box = patches.FancyBboxPatch(
          (xc - w_box / 2, y_feed - h_box / 2),
          w_box,
          h_box,
          boxstyle='round,pad=0.2,rounding_size=0.2',
          facecolor='#e0f2fe' if es_abierto else '#f1f5f9',
          edgecolor='#0284c7' if es_abierto else '#475569',
          lw=1.6,
          zorder=3,
      )
      ax.add_patch(fwh_box)

      ax.text(
          xc,
          y_feed - 0.15,
          f"{'Abierto' if es_abierto else 'Cerrado'} {i+1}",
          fontsize=7.6,
          **txt_m,
      )

      # Flecha de agua entre calentadores
      if i < n_fwh - 1:
        x_mitad = (xc + xs[i + 1]) / 2
        ax.annotate(
            '',
            xy=(xc + w_box / 2 + 0.1, y_feed),
            xytext=(x_mitad, y_feed),
            arrowprops=dict(arrowstyle='<-', color='#0369a1', lw=2.5),
        )

      if es_abierto:
        # Onditas de agua
        wx = np.linspace(xc - w_box / 2 + 0.15, xc + w_box / 2 - 0.15, 7)
        wy = [
            y_feed - 0.45 if k % 2 == 0 else y_feed - 0.38 for k in range(7)
        ]
        ax.plot(wx, wy, color='#0284c7', lw=1.2, zorder=4)

        b_pos_x = xc - w_box / 2 - 0.75
        b2 = patches.Circle(
            (b_pos_x, y_feed),
            0.45,
            facecolor='#edf2f7',
            edgecolor='#1a202c',
            lw=1.6,
            zorder=5,
        )
        ax.add_patch(b2)
        ax.text(b_pos_x, y_feed, 'Bomba 2', fontsize=7.4, zorder=6, **txt_m)

        # Salida y entrada de la Bomba 2
        st_sal_abierto = 4 if 4 in estados_ciclo else (st_cald_in - 2)
        st_sal_b2 = 5 if 5 in estados_ciclo else (st_cald_in - 1)
        etiqueta_estado(
            xc - w_box / 2 - 0.15,
            y_feed,
            st_sal_abierto,
            p_raw,
            None,
            pos='top',
        )
        etiqueta_estado(b_pos_x - 0.65, y_feed, st_sal_b2, pos='top')

      # Línea de drenaje en cascada con trampa
      if tiene_trampa:
        ax.plot(
            [xc, xc],
            [y_feed - h_box / 2, y_drain],
            color='#d97706',
            ls='--',
            lw=1.8,
            zorder=2,
        )

        x_dest = xs[i + 1] if i + 1 < n_fwh else 13.6
        y_dest = y_feed - h_box / 2 if i + 1 < n_fwh else 4.6
        ax.plot(
            [xc, x_dest, x_dest],
            [y_drain, y_drain, y_dest],
            color='#d97706',
            ls='--',
            lw=1.8,
            zorder=2,
        )

        # Símbolo de trampa de vapor
        x_trap = (xc + x_dest) / 2
        ax.plot(
            [x_trap - 0.2, x_trap + 0.2, x_trap - 0.2, x_trap + 0.2],
            [y_drain - 0.15, y_drain + 0.15, y_drain + 0.15, y_drain - 0.15],
            color='#b45309',
            lw=1.6,
            zorder=6,
        )

        # Estados de condensado saturado y salida de trampa
        # 3 es el drenaje de FWH3; 7 es el drenaje de FWH1
        st_dr = 7 if i == 0 else (3 if i == n_fwh - 1 else 5)
        etiqueta_estado(xc, y_drain + 0.45, st_dr, pos='top')

      # Extracción de vapor desde turbina
      x_top = (
          (4.8 if i == 0 else 10.2 + (i - 1) * 0.5)
          if tiene_recal
          else 5.2 + i * (5.5 / max(1, n_fwh))
      )
      ax.plot(
          [x_top, x_top, xc],
          [4.4, 3.2, 3.2],
          color='#64748b',
          ls='--',
          lw=1.8,
          zorder=2,
      )
      ax.plot(
          [xc, xc], [3.2, y_feed + h_box / 2], color='#64748b', ls='--', lw=1.8
      )
      ax.annotate(
          '',
          xy=(xc, y_feed + h_box / 2),
          xytext=(xc, y_feed + h_box / 2 + 0.35),
          arrowprops=dict(arrowstyle='-|>', color='#64748b', ls='--', lw=1.8),
      )

      # Mapeo dinámico de extracciones según los estados reales del ciclo
      if tiene_recal and n_fwh == 3:
            st_ext_lista = [12, 13, 10]
            st_ext = st_ext_lista[i] if i < len(st_ext_lista) else (12 + i)
      else:  
            st_ext = st_turb_in + (3 if tiene_recal else 1) + i

      etiqueta_estado(xc, 3.2, st_ext, p_raw, None, pos='top')   

      if y_val:
        ax.text(
            xc,
            2.4,
            f'y = {y_val:.4f}',
            fontsize=7.6,
            ha='center',
            va='center',
            color='#0f172a',
            fontweight='bold',
        )
  else:
    ax.plot([11.85, 1.45], [y_feed, y_feed], color='#0369a1', lw=3.0, zorder=2)
    etiqueta_estado(6.5, y_feed, st_b1_out, p_cald_kpa, None, pos='top')

  plt.tight_layout()
  return fig

# ==========================================
# VARIABLES POR DEFECTO
# ==========================================
defaults = {
    "tipo_planta": "Central de Potencia (Regenerativa / Recalentamiento)",
    "P_cald": 15000.0,
    "T_max": 600.0,
    "P_cond": 10.0,
    "m_dot": 15.0,
    "tiene_recal": True,
    "recal_optimo": True,
    "P_recal": 3750.0,
    "T_recal": 600.0,
    "num_fwh": 3,
    "fwh_data": [
        {"tipo": "Cerrado (CCA)", "presion": 4000.0, "drenaje": "Trampa de Vapor (En cascada)"},
        {"tipo": "Abierto (CAA)", "presion": 1200.0, "drenaje": "Mezcla Directa"},
        {"tipo": "Cerrado (CCA)", "presion": 250.0, "drenaje": "Trampa de Vapor (En cascada)"}
    ],
    "P_proc": 500.0,
    "frac_byp": 10.0,
    "frac_turb_proc": 70.0,
    "modo_cogen": "Modo Operativo Normal (Extracción Combinada)",
    "eta_t": 100.0,
    "eta_p": 100.0,
    "TH": 800.0,
    "T0": 300.0,
    "solucion_texto": ""
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================================
# BARRA LATERAL: ENTRADA Y PARÁMETROS
# ==========================================
st.sidebar.markdown("### ⚙️ Tipo de Instalación")
tipo_planta = st.sidebar.selectbox(
    "Seleccione el sistema térmico:",
    ["Central de Potencia (Regenerativa / Recalentamiento)", "Planta de Cogeneración (Calor y Potencia)"],
    index=0 if "Potencia" in st.session_state["tipo_planta"] else 1
)
st.session_state["tipo_planta"] = tipo_planta

st.sidebar.markdown("---")
st.sidebar.markdown("**Fronteras Térmicas Principales:**")
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=500.0)
T_max = st.sidebar.number_input("Temperatura Entrada Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=1.0)
m_dot = st.sidebar.number_input("Flujo Másico Total (ṁ) [kg/s]", value=float(st.session_state["m_dot"]), step=1.0)

# --- MÓDULO NUEVO: SOLUCIONADOR DE PROBLEMAS INVERSOS ---
st.sidebar.markdown("---")
modo_inverso = st.sidebar.checkbox("🔄 ¿Problema Inverso? (Hallar T_max por calidad)")
if modo_inverso:
    x_out_req = st.sidebar.slider("Calidad requerida a la salida (x)", 0.70, 1.00, 0.85, 0.01)
    try:
        # 1. Calculamos la entropía necesaria para tener esa calidad en el condensador
        s_f = CP.PropsSI('S', 'P', P_cond * 1e3, 'Q', 0, 'Water')
        s_g = CP.PropsSI('S', 'P', P_cond * 1e3, 'Q', 1, 'Water')
        s_req = s_f + x_out_req * (s_g - s_f)
        
        # 2. El programa viaja "hacia atrás" y descubre qué temperatura genera esa entropía
        T_max_calc = CP.PropsSI('T', 'P', P_cald * 1e3, 'S', s_req, 'Water') - 273.15
        
        # 3. Sobrescribimos la T_max con la respuesta exacta
        T_max = T_max_calc
        st.sidebar.success(f"🔥 T_max auto-calculada: **{T_max:.1f} °C**")
    except Exception as e:
        st.sidebar.error("Esas condiciones están fuera de la campana.")
# ---------------------------------------------------------
# ==========================================
# PARÁMETROS ESPECÍFICOS SEGÚN PLANTA
# ==========================================
fwh_configuracion = []
tiene_recal = False
P_recal, T_recal = 3750.0, 600.0
P_proc, frac_byp, frac_turb_proc, modo_cogen = 500.0, 10.0, 70.0, ""

if "Cogeneración" in tipo_planta:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Parámetros de Cogeneración:**")
    modo_cogen = st.sidebar.selectbox(
        "Modo de Operación:",
        [
            "Modo Operativo Normal (Extracción Combinada)",
            "Demanda Máxima de Calor (100% Proceso)",
            "Sin Demanda de Calor (100% Potencia Eléctrica)"
        ]
    )
    P_proc = st.sidebar.number_input("Presión Calentador de Proceso [kPa]", value=500.0, step=50.0)
    if "Normal" in modo_cogen:
        frac_byp = st.sidebar.slider("Fracción Estrangulada en Válvula de Desvío (%)", 0.0, 50.0, 10.0, 1.0)
        frac_turb_proc = st.sidebar.slider("Fracción Extraída en Turbina a P_proceso (%)", 0.0, 100.0, 70.0, 1.0)
    elif "Máxima" in modo_cogen:
        frac_byp, frac_turb_proc = 0.0, 100.0
    else:
        frac_byp, frac_turb_proc = 0.0, 0.0
else:
    st.sidebar.markdown("---")
    tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
    if tiene_recal:
        recal_opt = st.sidebar.checkbox("⚡ Usar Presión Óptima de Recalentamiento (0.25 · P_cald)", value=st.session_state["recal_optimo"])
        if recal_opt:
            P_recal = 0.25 * P_cald
            st.sidebar.info(f"Presión Óptima fijada: **{P_recal:.1f} kPa** ({(P_recal/1000):.2f} MPa)")
        else:
            P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=100.0)
        T_recal = st.sidebar.number_input("Temp. Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)

    st.sidebar.markdown("---")
    num_fwh = st.sidebar.number_input("Número de Calentadores (FWH)", min_value=0, max_value=8, value=int(st.session_state["num_fwh"]))
    for i in range(num_fwh):
        st.sidebar.markdown(f"**Calentador #{i+1}:**")
        col_t, col_p = st.sidebar.columns([1.2, 1])
        with col_t:
            t_sel = st.selectbox(f"Tipo #{i+1}", ["Cerrado (CCA)", "Abierto (CAA)"], index=0 if i % 2 == 0 else 1, key=f"t_{i}")
        with col_p:
            p_sug = float(P_cald / (i + 2))
            p_sel = st.number_input(f"P [kPa] #{i+1}", min_value=float(P_cond), max_value=float(P_cald), value=p_sug, step=100.0, key=f"p_{i}")
        
        dren_sel = "Mezcla Directa"
        if "Cerrado" in t_sel:
            dren_sel = st.sidebar.radio(
                f"Retorno de Condensado #{i+1}:",
                ["🪤 Trampa de Vapor (En cascada)", "⚙️ Bomba de Drenaje (Hacia adelante)"],
                key=f"dr_{i}"
            )

        fwh_configuracion.append({"tipo": t_sel, "presion": p_sel, "drenaje": dren_sel})

with st.sidebar.expander("Máquinas y Entorno (2da Ley)"):
    eta_t = st.slider("Isentrópica Turbina (η_t)", 0.50, 1.00, float(st.session_state["eta_t"]/100.0), 0.01)
    eta_p = st.slider("Isentrópica Bomba (η_p)", 0.50, 1.00, float(st.session_state["eta_p"]/100.0), 0.01)
    TH = st.number_input("Temp. Fuente (T_H) [K]", value=float(st.session_state["TH"]))
    T0 = st.number_input("Temp. Ambiente (T_0) [K]", value=float(st.session_state["T0"]))

st.sidebar.markdown("---")
color_ciclo = st.sidebar.color_picker("Color de la Línea del Ciclo", value="#00d2ff")
color_campana = st.sidebar.color_picker("Color de la Campana", value="#47505e")

# ==========================================
# CÁLCULOS TERMODINÁMICOS REALES (CoolProp)
# ==========================================
fluido = 'Water'
P_cald_Pa = P_cald * 1e3
P_cond_Pa = P_cond * 1e3
T_max_K = T_max + 273.15
P_recal_Pa = P_recal * 1e3
T_recal_K = T_recal + 273.15

def get_T_safe(P_val, H_val):
    try:
        hf = CP.PropsSI('H', 'P', P_val, 'Q', 0, fluido)
        hg = CP.PropsSI('H', 'P', P_val, 'Q', 1, fluido)
        if hf <= H_val <= hg:
            return CP.PropsSI('T', 'P', P_val, 'Q', 0, fluido) - 273.15
        return CP.PropsSI('T', 'P', P_val, 'H', H_val, fluido) - 273.15
    except Exception:
        return CP.PropsSI('T', 'P', P_val, 'Q', 0, fluido) - 273.15

def fmt_p(p_kpa):
    return f"{p_kpa/1000:.2f} MPa" if p_kpa >= 1000 else f"{p_kpa:.0f} kPa"

try:
    if "Cogeneración" in tipo_planta:
        P_proc_Pa = P_proc * 1e3
        h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
        s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)
        
        h_proc_iso = CP.PropsSI('H', 'P', P_proc_Pa, 'S', s_in_turb, fluido)
        h_proc_sal = h_in_turb - eta_t * (h_in_turb - h_proc_iso)
        s_proc_sal = CP.PropsSI('S', 'P', P_proc_Pa, 'H', h_proc_sal, fluido)
        T_proc_sal = get_T_safe(P_proc_Pa, h_proc_sal)
        
        h_cond_iso = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_in_turb, fluido)
        h_cond_in = h_in_turb - eta_t * (h_in_turb - h_cond_iso)
        s_cond_in = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_cond_in, fluido)
        T_cond_in = get_T_safe(P_cond_Pa, h_cond_in)
        
        h_cond_out = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
        s_cond_out = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
        v_cond = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
        T_cond_out = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15
        
        w_b1 = (v_cond * (P_proc_Pa - P_cond_Pa)) / eta_p
        h_b1_out = h_cond_out + w_b1
        
        hf_proc = CP.PropsSI('H', 'P', P_proc_Pa, 'Q', 0, fluido)
        sf_proc = CP.PropsSI('S', 'P', P_proc_Pa, 'Q', 0, fluido)
        vf_proc = 1 / CP.PropsSI('D', 'P', P_proc_Pa, 'Q', 0, fluido)
        T_sat_proc = CP.PropsSI('T', 'P', P_proc_Pa, 'Q', 0, fluido) - 273.15
        
        w_b2 = (vf_proc * (P_cald_Pa - P_proc_Pa)) / eta_p
        h_b2_out = hf_proc + w_b2
        
        f_byp = frac_byp / 100.0
        f_turb_in = 1.0 - f_byp
        f_proc_turb = f_turb_in * (frac_turb_proc / 100.0)
        f_cond = f_turb_in - f_proc_turb
        f_proc_total = f_byp + f_proc_turb
        
        q_proc_especifico = f_byp * (h_in_turb - hf_proc) + f_proc_turb * (h_proc_sal - hf_proc)
        Q_dot_proc = (m_dot * q_proc_especifico) / 1e3
        
        w_turb = f_turb_in * (h_in_turb - h_proc_sal) + f_cond * (h_proc_sal - h_cond_in)
        w_bombas = f_cond * w_b1 + f_proc_total * w_b2
        w_neto = w_turb - w_bombas
        W_dot_neto = (m_dot * w_neto) / 1e3
        
        h_in_cald = (f_cond * (h_b1_out + (v_cond * (P_cald_Pa - P_proc_Pa))/eta_p)) + (f_proc_total * h_b2_out)
        q_in = h_in_turb - h_in_cald
        Q_dot_in = (m_dot * q_in) / 1e3
        
        eps_u = ((W_dot_neto + Q_dot_proc) / Q_dot_in) * 100.0 if Q_dot_in > 0 else 0.0
        eta_th = (W_dot_neto / Q_dot_in) * 100.0 if Q_dot_in > 0 else 0.0
        w_rev = q_in * (1.0 - (T0 / TH))
        eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    else:
        # =================================================================
        # NUEVO MOTOR DE CÁLCULO: CICLO REGENERATIVO Y BALANCES DE MASA
        # =================================================================
        h_cond_out = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
        s_cond_out = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
        v_cond = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
        T_cond_out = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

        h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
        s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)

        fwh_ord = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)
        extracciones = []
        
        for f in fwh_ord:
            P_ext = f['presion'] * 1e3
            # CORRECCIÓN CLAVE 1: Signo '<' estrictamente, para extraer antes de recalentar
            if tiene_recal and P_ext < P_recal_Pa: 
                s_ref = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
                h_in_stage = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
            else:
                s_ref = s_in_turb
                h_in_stage = h_in_turb
            
            h_iso = CP.PropsSI('H', 'P', P_ext, 'S', s_ref, fluido)
            h_ext = h_in_stage - eta_t * (h_in_stage - h_iso)
            
            extracciones.append({
                'P': P_ext, 'h': h_ext, 'tipo': f['tipo'], 'drenaje': f['drenaje'],
                'hf': CP.PropsSI('H', 'P', P_ext, 'Q', 0, fluido),
                'Tsat': CP.PropsSI('T', 'P', P_ext, 'Q', 0, fluido) - 273.15,
                'vf': 1 / CP.PropsSI('D', 'P', P_ext, 'Q', 0, fluido),
                'y': 0.0
            })

        q_recal = 0.0
        if tiene_recal:
            h_rec_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
            h_rec_sal = h_in_turb - eta_t * (h_in_turb - h_rec_iso)
            h_rec_in2 = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
            s_rec_in2 = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
            q_recal_especifico = h_rec_in2 - h_rec_sal
            s_out_ref = s_rec_in2
            h_in_bp = h_rec_in2
        else:
            s_out_ref = s_in_turb
            h_in_bp = h_in_turb

        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_out_ref, fluido)
        h_out_turb = h_in_bp - eta_t * (h_in_bp - h_out_s)
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = get_T_safe(P_cond_Pa, h_out_turb)

        w_bombas_total = 0.0

        if len(extracciones) == 2 and "Cerrado" in extracciones[0]['tipo'] and "Abierto" in extracciones[1]['tipo']:
            ext1, ext2 = extracciones[0], extracciones[1]
            
            h_out_fwh1 = CP.PropsSI('H', 'P', P_cald_Pa, 'T', ext1['Tsat'] + 273.15, fluido)
            h_drain1 = ext1['hf']
            
            w_bomba1 = v_cond * (ext2['P'] - P_cond_Pa) / eta_p
            h_fw_in2 = h_cond_out + w_bomba1
            
            h_fw_out2 = ext2['hf']
            w_bomba2 = ext2['vf'] * (P_cald_Pa - ext2['P']) / eta_p
            h_fw_in1 = h_fw_out2 + w_bomba2
            
            if "Bomba" in ext1['drenaje']:
                # CORRECCIÓN CLAVE 2: Fórmula exacta de Çengel considerando masa (1-y1) en el tubo
                y1 = (h_out_fwh1 - h_fw_in1) / ((ext1['h'] - h_drain1) + (h_out_fwh1 - h_fw_in1))
                y2 = (1 - y1) * (h_fw_out2 - h_fw_in2) / (ext2['h'] - h_fw_in2)
                
                w_bomba_dren = ext1['vf'] * (P_cald_Pa - ext1['P']) / eta_p
                h_drain1_pumped = h_drain1 + w_bomba_dren
                
                h_in_cald = (1 - y1) * h_out_fwh1 + y1 * h_drain1_pumped
                w_bombas_total = (1 - y1 - y2) * w_bomba1 + (1 - y1) * w_bomba2 + y1 * w_bomba_dren
            else: 
                # Fórmula para trampa en cascada
                y1 = (h_out_fwh1 - h_fw_in1) / (ext1['h'] - h_drain1)
                y2 = (h_fw_out2 - (1 - y1) * h_fw_in2 - y1 * h_drain1) / (ext2['h'] - h_fw_in2)
                h_in_cald = h_out_fwh1
                w_bombas_total = (1 - y1 - y2) * w_bomba1 + (1.0) * w_bomba2

            w_t = 1.0 * (h_in_turb - ext1['h'])
            if tiene_recal:
                q_recal = (1 - y1) * q_recal_especifico
                w_t += (1 - y1) * (h_rec_in2 - ext2['h'])
            else:
                w_t += (1 - y1) * (ext1['h'] - ext2['h'])
            w_t += (1 - y1 - y2) * (ext2['h'] - h_out_turb)

        elif len(extracciones) == 2 and "Cerrado" in extracciones[0]['tipo'] and "Cerrado" in extracciones[1]['tipo']:
            ext1, ext2 = extracciones[0], extracciones[1]
            
            # Bomba del condensador impulsa el 100% del fluido a la caldera
            w_bomba1 = v_cond * (P_cald_Pa - P_cond_Pa) / eta_p
            h_fw_in2 = h_cond_out + w_bomba1
            
            # Salidas térmicas de los calentadores hacia la caldera
            h_fwh_out2 = CP.PropsSI('H', 'P', P_cald_Pa, 'T', ext2['Tsat'] + 273.15, fluido)
            h_fwh_out1 = CP.PropsSI('H', 'P', P_cald_Pa, 'T', ext1['Tsat'] + 273.15, fluido)
            
            # Balance Calentador 1 (alta presión)
            y1 = (h_fwh_out1 - h_fwh_out2) / (ext1['h'] - ext1['hf'])
            ext1['y'] = y1
            
            # Balance Calentador 2 (baja presión, recibe vapor ext2 + drenaje ext1)
            y2 = ((h_fwh_out2 - h_fw_in2) - y1 * (ext1['hf'] - ext2['hf'])) / (ext2['h'] - ext2['hf'])
            ext2['y'] = y2
            
            w_bombas_total = 1.0 * w_bomba1
            h_in_cald = h_fwh_out1
            
            w_t = (1.0 * (h_in_turb - ext1['h']) + 
                (1.0 - y1) * (ext1['h'] - ext2['h']) + 
                (1.0 - y1 - y2) * (ext2['h'] - h_out_turb))
        elif len(extracciones) == 3 and all("Abierto" in e['tipo'] for e in extracciones):
            ext1, ext2, ext3 = extracciones[0], extracciones[1], extracciones[2]
            
            # Bomba 1: Condensador -> P_ext3
            w_bomba1 = v_cond * (ext3['P'] - P_cond_Pa) / eta_p
            h_fw_in3 = h_cond_out + w_bomba1
            
            # Bomba 2: P_ext3 -> P_ext2
            w_bomba2 = ext3['vf'] * (ext2['P'] - ext3['P']) / eta_p
            h_fw_in2 = ext3['hf'] + w_bomba2
            
            # Bomba 3: P_ext2 -> P_ext1
            w_bomba3 = ext2['vf'] * (ext1['P'] - ext2['P']) / eta_p
            h_fw_in1 = ext2['hf'] + w_bomba3
            
            # Bomba 4: P_ext1 -> P_caldera
            w_bomba4 = ext1['vf'] * (P_cald_Pa - ext1['P']) / eta_p
            h_in_cald = ext1['hf'] + w_bomba4
            
            # Balances de masa y energía (despeje de fracciones y1, y2, y3)
            y1 = (ext1['hf'] - h_fw_in1) / (ext1['h'] - h_fw_in1)
            ext1['y'] = y1
            
            y2 = ((1.0 - y1) * (ext2['hf'] - h_fw_in2)) / (ext2['h'] - h_fw_in2)
            ext2['y'] = y2
            
            y3 = ((1.0 - y1 - y2) * (ext3['hf'] - h_fw_in3)) / (ext3['h'] - h_fw_in3)
            ext3['y'] = y3
            
            # Trabajo total de las 4 bombas
            w_bombas_total = ((1.0 - y1 - y2 - y3) * w_bomba1 + 
                            (1.0 - y1 - y2) * w_bomba2 + 
                            (1.0 - y1) * w_bomba3 + 
                            1.0 * w_bomba4)
            
            # Expansión en la turbina (4 tramos)
            w_t = (1.0 * (h_in_turb - ext1['h']) + 
                (1.0 - y1) * (ext1['h'] - ext2['h']) + 
                (1.0 - y1 - y2) * (ext2['h'] - ext3['h']) + 
                (1.0 - y1 - y2 - y3) * (ext3['h'] - h_out_turb))
            
        elif any("Abierto" in ext['tipo'] for ext in extracciones) and any("Cerrado" in ext['tipo'] for ext in extracciones):
            # 1. Ordenar extracciones de mayor presión a menor presión
            exts_ordenadas = sorted(extracciones, key=lambda x: x['P'], reverse=True)
            N = len(exts_ordenadas)
            
            # 2. Identificar el calentador abierto (desaireador)
            idx_open = [i for i, ext in enumerate(exts_ordenadas) if "Abierto" in ext['tipo']][0]
            ext_open = exts_ordenadas[idx_open]
            P_open = ext_open['P']
            
            # 3. Bombas del ciclo:
            # Bomba 1: Condensador hacia el desaireador a P_open
            w_bomba1 = v_cond * (P_open - P_cond_Pa) / eta_p
            h_fw_lp_in = h_cond_out + w_bomba1
            
            # Bomba 2: Desaireador hacia la caldera a P_caldera
            w_bomba2 = ext_open['vf'] * (P_cald_Pa - P_open) / eta_p
            h_fw_hp_in = ext_open['hf'] + w_bomba2
            
            # 4. Entalpías en el lado de los tubos para los cerrados
            h_fwh_out = [0.0] * N
            for i, ext in enumerate(exts_ordenadas):
                if "Cerrado" in ext['tipo']:
                    P_tubo = P_cald_Pa if i < idx_open else P_open
                    h_fwh_out[i] = CP.PropsSI('H', 'P', P_tubo, 'T', ext['Tsat'] + 273.15, fluido)
                else:
                    h_fwh_out[i] = ext['hf']
                    
            # Estado que entra a la caldera
            h_in_cald = h_fwh_out[0] if idx_open > 0 else h_fw_hp_in
            
            # 5. Balances térmicos para calcular las fracciones y_i
            y = [0.0] * N
            
            # --- ZONA DE ALTA PRESIÓN (Cerrados entre el desaireador y la caldera) ---
            drenaje_hp_h = 0.0
            masa_drenaje_hp = 0.0
            for i in range(idx_open):
                h_in_tubo = h_fwh_out[i + 1] if (i + 1 < idx_open) else h_fw_hp_in
                q_req = 1.0 * (h_fwh_out[i] - h_in_tubo)
                
                h_ext = exts_ordenadas[i]['h']
                hf_act = exts_ordenadas[i]['hf']
                calor_drenaje = masa_drenaje_hp * (drenaje_hp_h - hf_act) if masa_drenaje_hp > 0 else 0.0
                
                y[i] = (q_req - calor_drenaje) / (h_ext - hf_act)
                exts_ordenadas[i]['y'] = y[i]
                
                masa_drenaje_hp += y[i]
                drenaje_hp_h = hf_act
                
            # --- ZONA DE BAJA PRESIÓN (Cerrados entre el condensador y el desaireador) ---
            drenaje_lp_h = 0.0
            masa_drenaje_lp_rel = 0.0
            f_lp = [0.0] * N
            for i in range(idx_open + 1, N):
                h_in_tubo = h_fwh_out[i + 1] if (i + 1 < N) else h_fw_lp_in
                delta_h_tubo = (h_fwh_out[i] - h_in_tubo)
                h_ext = exts_ordenadas[i]['h']
                hf_act = exts_ordenadas[i]['hf']
                
                calor_dren = masa_drenaje_lp_rel * (drenaje_lp_h - hf_act) if masa_drenaje_lp_rel > 0 else 0.0
                f_lp[i] = (delta_h_tubo - calor_dren) / (h_ext - hf_act)
                masa_drenaje_lp_rel += f_lp[i]
                drenaje_lp_h = hf_act
                
            h_salida_lp_hacia_abierto = h_fwh_out[idx_open + 1] if (idx_open + 1 < N) else h_fw_lp_in
            
            # Balance en el Calentador Abierto (Desaireador)
            h_open = ext_open['h']
            hf_open = ext_open['hf']
            
            y_open = (hf_open - masa_drenaje_hp * drenaje_hp_h - (1.0 - masa_drenaje_hp) * h_salida_lp_hacia_abierto) / (h_open - h_salida_lp_hacia_abierto)
            y[idx_open] = y_open
            exts_ordenadas[idx_open]['y'] = y_open
            
            # Fracciones definitivas de baja presión
            m_lp = 1.0 - masa_drenaje_hp - y_open
            for i in range(idx_open + 1, N):
                y[i] = m_lp * f_lp[i]
                exts_ordenadas[i]['y'] = y[i]
                
            # 6. Trabajo total de bombas
            w_bombas_total = m_lp * w_bomba1 + 1.0 * w_bomba2
            
            # 7. Trabajo de la turbina por tramos
            w_t = 0.0
            m_turb = 1.0
            h_ant = h_in_turb
            
            for i in range(N):
                h_act = exts_ordenadas[i]['h']
                w_t += m_turb * (h_ant - h_act)
                m_turb -= y[i]
                h_ant = h_act
                
            w_t += m_turb * (h_ant - h_out_turb)

        elif len(extracciones) == 1 and "Cerrado" in extracciones[0]['tipo']:
            ext1 = extracciones[0]
            P_ext = ext1['P']
            
            # 1. Bomba del condensador envía todo el flujo a P_caldera
            w_bomba1 = v_cond * (P_cald_Pa - P_cond_Pa) / eta_p
            h_fw_in = h_cond_out + w_bomba1
            
            # 2. Salida del calentador: agua líquida a Tsat(P_ext) a presión de caldera
            h_fwh_out = CP.PropsSI('H', 'P', P_cald_Pa, 'T', ext1['Tsat'] + 273.15, fluido)
            h_drain = ext1['hf']
            
            # 3. Balance de energía en el CCA: y * (h_ext - h_drain) = (1.0) * (h_fwh_out - h_fw_in)
            ext1['y'] = (h_fwh_out - h_fw_in) / (ext1['h'] - h_drain)
            y = ext1['y']
            
            # 4. Trabajo de bombas y turbina
            w_bombas_total = 1.0 * w_bomba1
            
            if tiene_recal:
                w_t = 1.0 * (h_in_turb - ext1['h']) + (1 - y) * (h_in_bp - h_out_turb)
                q_recal = (1 - y) * q_recal_especifico
            else:
                w_t = 1.0 * (h_in_turb - ext1['h']) + (1 - y) * (ext1['h'] - h_out_turb)
                q_recal = 0.0
                
            h_in_cald = h_fwh_out
        elif (
                len(extracciones) == 2
                and "Abierto" in extracciones[0]["tipo"]
                and "Abierto" in extracciones[1]["tipo"]
            ):
            ext1, ext2 = extracciones[0], extracciones[1]

            # 1. Bomba 1: Desde condensador hasta P_ext2
            w_bomba1 = v_cond * (ext2["P"] - P_cond_Pa) / eta_p
            h_fw_in2 = h_cond_out + w_bomba1

            # 2. Bomba 2: Desde P_ext2 hasta P_ext1
            w_bomba2 = ext2["vf"] * (ext1["P"] - ext2["P"]) / eta_p
            h_fw_in1 = ext2["hf"] + w_bomba2

            # 3. Bomba 3: Desde P_ext1 hasta P_caldera
            w_bomba3 = ext1["vf"] * (P_cald_Pa - ext1["P"]) / eta_p
            h_in_cald = ext1["hf"] + w_bomba3

            # Balances de materia y energía en los calentadores abiertos
            y1 = (ext1["hf"] - h_fw_in1) / (ext1["h"] - h_fw_in1)
            ext1["y"] = y1

            y2 = ((1.0 - y1) * (ext2["hf"] - h_fw_in2)) / (ext2["h"] - h_fw_in2)
            ext2["y"] = y2

            # Trabajo total de las tres bombas
            w_bombas_total = (
                (1.0 - y1 - y2) * w_bomba1 + (1.0 - y1) * w_bomba2 + (1.0) * w_bomba3
            )

            # Trabajo de la turbina expandiéndose en 3 etapas
            w_t = (
                1.0 * (h_in_turb - ext1["h"])
                + (1.0 - y1) * (ext1["h"] - ext2["h"])
                + (1.0 - y1 - y2) * (ext2["h"] - h_out_turb)
            )

        elif len(extracciones) == 1 and "Abierto" in extracciones[0]['tipo']:
            ext1 = extracciones[0]
            P_ext = ext1['P']
            w_bomba1 = v_cond * (P_ext - P_cond_Pa) / eta_p
            h_fw_in = h_cond_out + w_bomba1
            h_fwh_out = ext1['hf']
            v_fwh = ext1['vf']
            ext1['y'] = (h_fwh_out - h_fw_in) / (ext1['h'] - h_fw_in)
            y = ext1['y']
            w_bomba2 = v_fwh * (P_cald_Pa - P_ext) / eta_p
            h_in_cald = h_fwh_out + w_bomba2
            w_bombas_total = (1 - y) * w_bomba1 + (1.0) * w_bomba2
            if tiene_recal:
                # 1. Turbina de alta + Turbina de baja (recalentada con flujo restante)
                w_t = 1.0 * (h_in_turb - ext1['h']) + (1 - y) * (h_in_bp - h_out_turb)
                # 2. El recalentador solo recibe la masa que no fue extraída (1 - y)
                q_recal = (1 - y) * q_recal_especifico
            else:
                # Ciclo regenerativo estándar sin recalentamiento
                w_t = 1.0 * (h_in_turb - ext1['h']) + (1 - y) * (ext1['h'] - h_out_turb)
                q_recal = 0.0
        else:
            # 1. Primero calculamos el trabajo de la bomba para el ciclo simple
            w_bombas_total = v_cond * (P_cald_Pa - P_cond_Pa) / eta_p
            h_out_cond = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
            h_in_cald = h_out_cond + w_bombas_total
            w_t = h_in_turb - h_out_turb

        q_in = (h_in_turb - h_in_cald) + q_recal
        w_neto = w_t - w_bombas_total
        W_dot_neto = (m_dot * w_neto) / 1e3
        Q_dot_in = (m_dot * q_in) / 1e3
        Q_dot_proc = 0.0
        eps_u = (w_neto / q_in) * 100.0 if q_in > 0 else 0.0
        eta_th = eps_u
        w_rev = q_in * (1.0 - (T0 / TH))
        eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

        h2 = h_in_cald
        s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
        T2 = get_T_safe(P_cald_Pa, h2)

    # ==========================================
    # GENERADOR DE MEMORIA ANALÍTICA
    # ==========================================
    def generar_memoria_analitica_completa():
        if "Cogeneración" in tipo_planta:
            return f"""### 1. Memoria de Cálculo: Planta de Cogeneración Industrial
* **Flujo másico total en caldera (ṁ):** {m_dot:.2f} kg/s
* **Condición de vapor vivo:** P = {P_cald:.0f} kPa ({fmt_p(P_cald)}), T = {T_max:.1f} °C
  * Entalpía de vapor vivo (h1): **{h_in_turb/1e3:.2f} kJ/kg**
* **Presión del calentador de proceso (P_proc):** {P_proc:.0f} kPa ({fmt_p(P_proc)})
  * Entalpía extracción turbina: **{h_proc_sal/1e3:.2f} kJ/kg**
  * Entalpía líquido saturado proceso (h_f,proc): **{hf_proc/1e3:.2f} kJ/kg**
* **Condición del Condensador:** P = {P_cond:.1f} kPa
  * Entalpía de escape turbina: **{h_cond_in/1e3:.2f} kJ/kg**
  * Entalpía líquido saturado (h_f,cond): **{h_cond_out/1e3:.2f} kJ/kg**

---

### 2. Distribución de Flujos Másicos y Balances
* **Fracción estrangulada en válvula de desvío (f_byp):** **{f_byp*100:.1f} %** ({m_dot*f_byp:.2f} kg/s)
* **Fracción hacia calentador de proceso desde turbina:** **{f_proc_turb*100:.1f} %** ({m_dot*f_proc_turb:.2f} kg/s)
* **Fracción total a proceso:** **{f_proc_total*100:.1f} %** ({m_dot*f_proc_total:.2f} kg/s)
* **Fracción remanente al condensador:** **{f_cond*100:.1f} %** ({m_dot*f_cond:.2f} kg/s)

---

### 3. Resultados Energéticos y Factor de Utilización
* **Tasa de Calor Suministrado (Q_in):** **{Q_dot_in:.2f} MW**
* **Tasa de Suministro de Calor de Proceso (Q_proceso):** **{Q_dot_proc:.2f} MW**
* **Potencia Neta Generada (W_neto):** **{W_dot_neto:.2f} MW**
* **Eficiencia Térmica de Generación (η_th):** **{eta_th:.2f} %**
* **Factor de Utilización (ε_u):**
  $$\\epsilon_u = \\frac{{\\dot{{W}}_{{neto}} + \\dot{{Q}}_{{proceso}}}}{{\\dot{{Q}}_{{in}}}} = \\mathbf{{{eps_u:.2f} \\%}}$$
"""
        else:
            fwh_ord = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)
            doc = f"""### 1. Parámetros de Diseño y Fronteras del Sistema
* **Presión de Caldera:** {P_cald:.1f} kPa ({fmt_p(P_cald)})
* **Temperatura Entrada Turbina (T_max):** {T_max:.1f} °C
* **Presión de Condensación:** {P_cond:.1f} kPa
* **Recalentamiento Intermedio:** {"Sí, a " + str(P_recal) + " kPa (" + fmt_p(P_recal) + ") y " + str(T_recal) + " °C" if tiene_recal else "No"}
* **Calentadores de Agua de Alimentación (FWH):** {num_fwh} configurados
* **Rendimientos Isentrópicos:** Turbina η_t = {eta_t*100:.1f}%, Bombas η_p = {eta_p*100:.1f}%

---

### 2. Configuración de Calentadores y Mecanismos de Retorno
"""
            for idx, f in enumerate(fwh_ord):
                mecanismo = f['drenaje']
                doc += f"* **Calentador #{idx+1} ({f['tipo']}):** P = {f['presion']:.0f} kPa ({fmt_p(f['presion'])})\n"
                doc += f"  * Mecanismo: **{mecanismo}**\n"
                if "Trampa" in mecanismo:
                    doc += "    * *Comportamiento termodinámico:* Expansión isoentálpica en cascada ($h = \\text{cte}$) hacia menor presión sin consumo de trabajo de bomba.\n"
                elif "Bomba" in mecanismo:
                    doc += "    * *Comportamiento termodinámico:* Bombeo hacia adelante ($w_b = v \\Delta P / \\eta_p$) inyectando el condensado en la línea de alta presión.\n"
            
            doc += f"""\n---

### 3. Resultados Energéticos y de Segunda Ley
* **Trabajo neto específico (w_neto):** **{w_neto/1e3:.2f} kJ/kg**
* **Calor total suministrado (q_in):** **{q_in/1e3:.2f} kJ/kg**
* **Potencia Total Generada (W_neto para ṁ = {m_dot:.1f} kg/s):** **{W_dot_neto:.2f} MW**
* **Eficiencia Térmica (η_th):** **{eta_th:.2f} %**
* **Eficiencia de la Segunda Ley (η_II):** **{eta_II:.2f} %**
"""
            return doc

    st.sidebar.markdown("---")
    if st.sidebar.button("⚡ Calcular Procedimiento Paso a Paso", type="primary", use_container_width=True):
        st.session_state["solucion_texto"] = generar_memoria_analitica_completa()
        st.sidebar.success("¡Memoria de cálculo generada!")
        st.rerun()

    # ==========================================
    # PESTAÑAS PRINCIPALES
    # ==========================================
    tab_ts, tab_diagrama, tab_estados, tab_procedimiento = st.tabs([
        "📈 Diagrama T-s Interactivo",
        "🏭 Diagrama de Equipos", 
        "📋 Estados Termodinámicos", 
        "📝 Memoria de Cálculo"
    ])

    with tab_ts:
        T_crit = CP.PropsSI('Tcrit', fluido)
        T_campana = np.linspace(273.16, T_crit - 0.2, 250)
        s_liq = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
        s_vap = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=s_liq + s_vap[::-1],
            y=[t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]],
            mode='lines',
            line=dict(color=color_campana, width=1.4),
            name='Campana',
            hoverinfo='skip'
        ))

        T_sat_cald = CP.PropsSI('T', 'P', P_cald_Pa, 'Q', 0, fluido) - 273.15
        s_f_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 0, fluido) / 1e3
        s_g_cald = CP.PropsSI('S', 'P', P_cald_Pa, 'Q', 1, fluido) / 1e3
        T_sup = np.linspace(T_sat_cald + 0.5, T_max, 30)
        s_sup = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t + 273.15, fluido)/1e3 for t in T_sup]

        if "Cogeneración" in tipo_planta:
            pt_cond_liq = (s_cond_out/1e3, T_cond_out)
            pt_b1 = (s_cond_out/1e3, T_cond_out + 20.0)
            pt_proc_liq = (sf_proc/1e3, T_sat_proc)
            pt_b2 = (sf_proc/1e3, T_sat_proc + 25.0)
            pt_in = (s_in_turb/1e3, T_max)
            pt_ext = (s_proc_sal/1e3, T_proc_sal)
            pt_esc = (s_cond_in/1e3, T_cond_in)

            x_cogen = [pt_cond_liq[0], pt_b1[0], pt_proc_liq[0], pt_b2[0], s_f_cald, s_g_cald] + list(s_sup) + [pt_in[0], pt_ext[0], pt_esc[0], pt_cond_liq[0]]
            y_cogen = [pt_cond_liq[1], pt_b1[1], pt_proc_liq[1], pt_b2[1], T_sat_cald, T_sat_cald] + list(T_sup) + [pt_in[1], pt_ext[1], pt_esc[1], pt_cond_liq[1]]

            fig.add_trace(go.Scatter(
                x=x_cogen, y=y_cogen,
                mode='lines', line=dict(color=color_ciclo, width=2.4),
                name='Ciclo de Potencia'
            ))

            sg_proc = CP.PropsSI('S', 'P', P_proc_Pa, 'Q', 1, fluido) / 1e3
            fig.add_trace(go.Scatter(
                x=[pt_ext[0], sg_proc, pt_proc_liq[0]],
                y=[pt_ext[1], T_sat_proc, pt_proc_liq[1]],
                mode='lines', line=dict(color='#ff9f1c', width=2.2, dash='solid'),
                name='Calor de Proceso'
            ))

            fig.add_trace(go.Scatter(
                x=[pt_in[0], pt_ext[0] + 0.3],
                y=[pt_in[1], T_sat_proc],
                mode='lines', line=dict(color='#ef4444', width=1.8, dash='dot'),
                name='Válvula de Desvío (Bypass)'
            ))

            pts_x = [pt_cond_liq[0], pt_proc_liq[0], pt_b2[0], pt_in[0], pt_ext[0], pt_esc[0]]
            pts_y = [pt_cond_liq[1], pt_proc_liq[1], pt_b2[1], pt_in[1], pt_ext[1], pt_esc[1]]
            pts_txt = ["Condensador", "Calentador Proceso", "Salida Bomba", "Entrada Turbina", "Extracción Proceso", "Escape"]

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y, mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt, textposition="top right",
                textfont=dict(color='white', size=10, family="Inter", weight='bold')
            ))

            anotaciones = [
                dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{fmt_p(P_cald)}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(pt_proc_liq[0] + pt_ext[0])/2, y=T_sat_proc + 10, text=f"<b>Proceso: {fmt_p(P_proc)} ◀</b>", showarrow=False, font=dict(color='#ff9f1c', size=11)),
                dict(x=(pt_cond_liq[0] + pt_esc[0])/2, y=T_cond_out + 10, text=f"<b>{fmt_p(P_cond)}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
            ]

        else:
            fwh_ord = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)
            pts_x, pts_y, pts_txt, pts_pos = [], [], [], []
            contador = 1

            pt1 = (s_cond_out/1e3, T_cond_out)
            pt2 = (s_cond_out/1e3, T_cond_out + 22.0)
            pts_x.extend([pt1[0], pt2[0]])
            pts_y.extend([pt1[1], pt2[1]])
            pts_txt.extend([str(contador), str(contador+1)])
            pts_pos.extend(["bottom left", "top left"])
            contador += 2

            pts_liq = [pt1, pt2]
            fwh_inv = list(reversed(fwh_ord))

            for f in fwh_inv:
                p_pa = f['presion'] * 1e3
                t_sf = CP.PropsSI('T', 'P', p_pa, 'Q', 0, fluido) - 273.15
                s_sf = CP.PropsSI('S', 'P', p_pa, 'Q', 0, fluido) / 1e3

                t_tr = np.linspace(pts_liq[-1][1], t_sf, 12)
                s_tr = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in t_tr]
                for sx, ty in zip(s_tr, t_tr):
                    pts_liq.append((sx, ty))

                pt_f = (s_sf, t_sf)
                pt_b = (s_sf, t_sf + 16.0)
                pts_liq.extend([pt_f, pt_b])

                pts_x.extend([pt_f[0], pt_b[0]])
                pts_y.extend([pt_f[1], pt_b[1]])
                pts_txt.extend([str(contador), str(contador+1)])
                pts_pos.extend(["bottom left", "top left"])
                contador += 2

            t_cald = np.linspace(pts_liq[-1][1], T_sat_cald, 18)
            s_cald = [CP.PropsSI('S', 'T', t + 273.15, 'Q', 0, fluido)/1e3 for t in t_cald]
            for sx, ty in zip(s_cald, t_cald):
                pts_liq.append((sx, ty))

            pt_in_t = (s_in_turb/1e3, T_max)
            pts_cald = [(s_f_cald, T_sat_cald), (s_g_cald, T_sat_cald)] + list(zip(s_sup, T_sup))

            pts_x.append(pt_in_t[0])
            pts_y.append(pt_in_t[1])
            pts_txt.append(str(contador))
            pts_pos.append("middle right")
            contador += 1

            x_main = [p[0] for p in pts_liq] + [p[0] for p in pts_cald]
            y_main = [p[1] for p in pts_liq] + [p[1] for p in pts_cald]

            if tiene_recal:
                h_rec_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
                t_rec_sal_val = get_T_safe(P_recal_Pa, h_rec_iso)
                pt_rec_s = (s_in_turb/1e3, t_rec_sal_val)
                x_main.append(pt_rec_s[0])
                y_main.append(pt_rec_s[1])
                pts_x.append(pt_rec_s[0])
                pts_y.append(pt_rec_s[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

                T_rec_c = np.linspace(t_rec_sal_val + 0.5, T_recal, 15)
                s_rec_c = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t + 273.15, fluido)/1e3 for t in T_rec_c]
                for sx, ty in zip(s_rec_c, T_rec_c):
                    x_main.append(sx)
                    y_main.append(ty)

                pt_in_bp = (s_rec_in2/1e3, T_recal)
                pts_x.append(pt_in_bp[0])
                pts_y.append(pt_in_bp[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

            for idx, f in enumerate(fwh_ord):
                p_pa = f['presion'] * 1e3
                t_sf = CP.PropsSI('T', 'P', p_pa, 'Q', 0, fluido) - 273.15
                s_sf = CP.PropsSI('S', 'P', p_pa, 'Q', 0, fluido) / 1e3
                s_sg = CP.PropsSI('S', 'P', p_pa, 'Q', 1, fluido) / 1e3
                h_g = CP.PropsSI('H', 'P', p_pa, 'Q', 1, fluido)

                s_origen = (s_in_turb/1e3) if (tiene_recal and p_pa >= P_recal_Pa) else (s_rec_in2/1e3 if tiene_recal else s_in_turb/1e3)
                h_ext = CP.PropsSI('H', 'P', p_pa, 'S', s_origen * 1e3, fluido)
                t_ext = get_T_safe(p_pa, h_ext)
                pt_ext = (s_origen, t_ext)

                if h_ext > h_g + 2000.0 and t_ext > t_sf + 1.0:
                    t_iso = np.linspace(t_ext, t_sf + 0.6, 8)
                    s_iso = [CP.PropsSI('S', 'P', p_pa, 'T', t + 273.15, fluido)/1e3 for t in t_iso]
                    x_ext = s_iso + [s_sg, s_sf]
                    y_ext = list(t_iso) + [t_sf, t_sf]
                else:
                    x_ext = [s_origen, s_sf]
                    y_ext = [t_sf, t_sf]

                fig.add_trace(go.Scatter(
                    x=x_ext, y=y_ext, mode='lines',
                    line=dict(color=color_ciclo, width=1.8, dash='solid'),
                    name=f'Extracción {fmt_p(p_pa/1000)}',
                    hoverinfo='skip'
                ))

                if "Trampa" in f['drenaje']:
                    p_inferior = fwh_ord[idx+1]['presion']*1e3 if idx+1 < len(fwh_ord) else P_cond_Pa
                    t_inferior = CP.PropsSI('T', 'P', p_inferior, 'Q', 0, fluido) - 273.15
                    s_sf_inf = CP.PropsSI('S', 'P', p_inferior, 'Q', 0, fluido) / 1e3
                    
                    fig.add_trace(go.Scatter(
                        x=[s_sf, s_sf + 0.15],
                        y=[t_sf, t_inferior],
                        mode='lines',
                        line=dict(color='#f59e0b', width=1.6, dash='dash'),
                        name=f'Trampa #{idx+1} (h=cte)',
                        hoverinfo='skip'
                    ))

                pts_x.append(pt_ext[0])
                pts_y.append(pt_ext[1])
                pts_txt.append(str(contador))
                pts_pos.append("middle right")
                contador += 1

            pt_esc = (s_out_turb/1e3, T_out_turb)
            x_main.extend([pt_esc[0], pt1[0]])
            y_main.extend([pt_esc[1], pt1[1]])

            pts_x.append(pt_esc[0])
            pts_y.append(pt_esc[1])
            pts_txt.append(str(contador))
            pts_pos.append("middle right")

            fig.add_trace(go.Scatter(
                x=x_main, y=y_main, mode='lines',
                line=dict(color=color_ciclo, width=2.4),
                name='Ciclo Principal', hoverinfo='skip'
            ))

            fig.add_trace(go.Scatter(
                x=pts_x, y=pts_y, mode='markers+text',
                marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
                text=pts_txt, textposition=pts_pos,
                textfont=dict(color='white', size=11, family="Inter", weight='bold'),
                name='Estados'
            ))

            anotaciones = [
                dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{fmt_p(P_cald)}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
                dict(x=(s_cond_out/1e3 + s_out_turb/1e3)/2, y=T_cond_out + 10, text=f"<b>{fmt_p(P_cond)}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
            ]

        fig.update_layout(
            paper_bgcolor='#111317',
            plot_bgcolor='#111317',
            margin=dict(l=55, r=40, t=30, b=45),
            xaxis=dict(
                title=dict(text='s [kJ/kg · K]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229', zeroline=False, showgrid=True, gridwidth=1, range=[0.0, 9.2]
            ),
            yaxis=dict(
                title=dict(text='T [°C]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229', zeroline=False, showgrid=True, gridwidth=1,
                range=[-10, max(660.0, T_max + 40.0)]
            ),
            showlegend=False,
            height=580,
            annotations=anotaciones
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_diagrama:
        st.subheader("Esquema de Planta y Distribución de Flujos")

        # 1. Extracción de estados calculados
        estados_dict = {}
        if 'pts_txt' in locals() and 'pts_y' in locals():
            for txt, py in zip(pts_txt, pts_y):
                try:
                    estados_dict[int(txt)] = {'T': float(py)}
                except Exception:
                    pass

        lista_estados = locals().get('estados', locals().get('datos_estados', None))
        if isinstance(lista_estados, (list, tuple)):
            for i, est in enumerate(lista_estados):
                if isinstance(est, dict):
                    p_v = est.get('P', est.get('p', 0))
                    t_v = est.get('T', est.get('t', 0))
                    p_c = p_v / 1e3 if p_v > 50000 else p_v
                    t_c = t_v - 273.15 if t_v > 200 else t_v
                    if (i + 1) in estados_dict:
                        estados_dict[i + 1]['P'] = p_c
                        if 'T' not in estados_dict[i + 1]:
                            estados_dict[i + 1]['T'] = t_c
                    else:
                        estados_dict[i + 1] = {'P': p_c, 'T': t_c}

        # 2. Detección segura de recalentamiento y presiones
        tiene_recal_val = False
        for var_name in ['tiene_recal', 'recalentamiento', 'hay_recal', 'tiene_recalentamiento', 'chk_recal']:
            if var_name in locals() and locals()[var_name]:
                tiene_recal_val = True
                break

        p_rec_val = locals().get('P_recal_Pa', locals().get('P_recal', locals().get('P_rec', None)))
        t_rec_val = locals().get('T_recal', locals().get('T_rec', None))

        # 3. Potencias y calores
        m_dot_val = locals().get('m_dot', 1.0)
        q_in_kw = locals().get('Q_dot_in', locals().get('q_in', 0) * m_dot_val if 'q_in' in locals() else None)
        w_neto_kw = locals().get('W_dot_neto', locals().get('w_neto', 0) * m_dot_val if 'w_neto' in locals() else None)
        q_cond_kw = locals().get('Q_dot_out', locals().get('q_out', 0) * m_dot_val if 'q_out' in locals() else None)

        # 4. Generación y renderizado seguro del gráfico
        try:
            fig_planta = dibujar_diagrama_planta(
                p_cald_kpa=locals().get('P_cald', 15000.0),
                t_cald=locals().get('T_cald', locals().get('T_in_turb', 600.0)),
                p_cond_kpa=locals().get('P_cond', 10.0),
                fwh_ord=locals().get('fwh_ord', []),
                tiene_recal=tiene_recal_val,
                p_recal_kpa=p_rec_val,
                t_recal=t_rec_val,
                estados_ciclo=estados_dict,
                w_t_total=w_neto_kw,
                q_in_total=q_in_kw,
                q_out_cond=q_cond_kw
            )
            st.pyplot(fig_planta, use_container_width=True)
            plt.close(fig_planta)
        except Exception as e:
            st.error(f"Error al generar el diagrama de planta: {e}")

    with tab_estados:
        st.markdown(f"#### Estados Termodinámicos Fundamentales ({tipo_planta})")
        if "Cogeneración" in tipo_planta:
            filas_cogen = [
                {"Equipo / Punto": "1. Entrada Turbina (Caldera)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h_in_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_in_turb/1e3:.4f}"},
                {"Equipo / Punto": "2. Extracción Turbina a Proceso", "P [kPa]": f"{P_proc:.1f}", "T [°C]": f"{T_proc_sal:.1f}", "h [kJ/kg]": f"{h_proc_sal/1e3:.2f}", "s [kJ/kg·K]": f"{s_proc_sal/1e3:.4f}"},
                {"Equipo / Punto": "3. Salida Turbina a Condensador", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_cond_in:.1f}", "h [kJ/kg]": f"{h_cond_in/1e3:.2f}", "s [kJ/kg·K]": f"{s_cond_in/1e3:.4f}"},
                {"Equipo / Punto": "4. Salida Condensador (Líq. Sat.)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_cond_out:.1f}", "h [kJ/kg]": f"{h_cond_out/1e3:.2f}", "s [kJ/kg·K]": f"{s_cond_out/1e3:.4f}"},
                {"Equipo / Punto": "5. Salida Calentador Proceso (Líq. Sat.)", "P [kPa]": f"{P_proc:.1f}", "T [°C]": f"{T_sat_proc:.1f}", "h [kJ/kg]": f"{hf_proc/1e3:.2f}", "s [kJ/kg·K]": f"{sf_proc/1e3:.4f}"}
            ]
            st.dataframe(filas_cogen, use_container_width=True, hide_index=True)
        else:
            filas = [
                {"Estado": "Salida Condensador (1)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_cond_out:.1f}", "h [kJ/kg]": f"{h_cond_out/1e3:.2f}", "s [kJ/kg·K]": f"{s_cond_out/1e3:.4f}"},
                {"Estado": "Entrada de Agua a Caldera", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
                {"Estado": "Entrada Turbina AP", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h_in_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_in_turb/1e3:.4f}"},
                {"Estado": "Escape Turbina / Condensador", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_out_turb:.1f}", "h [kJ/kg]": f"{h_out_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_out_turb/1e3:.4f}"}
            ]
            st.dataframe(filas, use_container_width=True, hide_index=True)

    with tab_procedimiento:
        st.markdown("#### Memoria de Cálculo Analítica Paso a Paso")
        col_btn, _ = st.columns([1.5, 2])
        with col_btn:
            if st.button("⚡ Generar / Actualizar Memoria de Cálculo", type="primary", use_container_width=True):
                st.session_state["solucion_texto"] = generar_memoria_analitica_completa()
                st.rerun()

        if st.session_state["solucion_texto"]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.markdown(st.session_state["solucion_texto"])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Presiona el botón **'⚡ Generar / Actualizar Memoria de Cálculo'** para desplegar el balance de masa, energía y factor de utilización.")

except Exception as err:
    st.error(f"Error procesando propiedades en CoolProp: {err}")
