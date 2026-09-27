import streamlit as st
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np
import json
import time
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILO ELEGANTE
# ==========================================
st.set_page_config(
    page_title="TermoRankine Pro | Simulador & Solucionador",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    .main-hero {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.8rem 2.2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
    }
    
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.02em;
        margin: 0;
    }
    
    .hero-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.4rem;
        line-height: 1.4;
    }
    
    .solution-box {
        background: #0b1120;
        border: 1px solid #1e293b;
        border-left: 4px solid #38bdf8;
        border-radius: 12px;
        padding: 1.6rem;
        margin: 1.5rem 0;
        line-height: 1.6;
    }
    
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #e2e8f0;
        margin: 1.5rem 0 0.8rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        padding-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-hero">
    <div class="hero-title">⚡ TermoRankine Pro</div>
    <div class="hero-subtitle">Simulador termodinámico avanzado: diagramas T-s estilo Çengel, Primera y Segunda Ley, y resolución analítica guiada por IA.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
client = genai.Client(api_key=API_KEY)

# ==========================================
# VARIABLES POR DEFECTO
# ==========================================
defaults = {
    "P_cald": 15000.0,
    "T_max": 600.0,
    "P_cond": 10.0,
    "tiene_recal": True,
    "P_recal": 4000.0,
    "T_recal": 600.0,
    "num_fwh": 2,
    "fwh_data": [
        {"tipo": "Cerrado (Closed)", "presion": 4000.0},
        {"tipo": "Abierto (Open)", "presion": 500.0}
    ],
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
# MÉTODO DE ENTRADA
# ==========================================
metodo = st.radio(
    "Selecciona cómo ingresar los datos del problema:",
    ["📷 Cargar Captura / Imagen del Problema", "✍️ Configurar Datos Manualmente a Mano"],
    horizontal=True
)

if metodo == "📷 Cargar Captura / Imagen del Problema":
    col_subir, col_prev = st.columns([1.2, 1.8])
    with col_subir:
        archivo = st.file_uploader("Arrastra o selecciona la captura del libro o examen", type=["png", "jpg", "jpeg", "webp"])
        btn_ia = st.button("🚀 Resolver con IA", type="primary", use_container_width=True) if archivo else False

    with col_prev:
        if archivo:
            img = Image.open(archivo)
            st.image(img, caption="Problema cargado", use_container_width=True)
            if btn_ia:
                with st.spinner("Analizando ciclo, extrayendo parámetros y resolviendo..."):
                    prompt = """
                    Eres un profesor titular de Termodinámica de ingeniería. Analiza la imagen.
                    Devuelve ÚNICAMENTE un JSON con:
                    {
                      "P_cald_kPa": float,
                      "T_max_C": float,
                      "P_cond_kPa": float,
                      "tiene_recal": bool,
                      "P_recal_kPa": float o null,
                      "T_recal_C": float o null,
                      "num_fwh": int,
                      "fwh_lista": [
                         {"tipo": "Abierto (Open)" o "Cerrado (Closed)", "presion_kPa": float}
                      ],
                      "eta_t": float,
                      "eta_p": float,
                      "TH_K": float,
                      "T0_K": float,
                      "respuestas_directas": "Markdown directo respondiendo TODOS los incisos (a, b, fracciones extraídas, trabajo neto, eficiencia térmica, exergía) con valores finales en negrita."
                    }
                    Reglas: presiones en kPa (15 MPa = 15000, 4 MPa = 4000, 0.5 MPa = 500).
                    """
                    datos = None
                    for intento in range(3):
                        try:
                            res = client.models.generate_content(
                                model="gemini-flash-latest",
                                contents=[img, prompt],
                                config=types.GenerateContentConfig(response_mime_type="application/json")
                            )
                            datos = json.loads(res.text)
                            break
                        except Exception:
                            time.sleep(2)

                    if datos:
                        st.session_state["P_cald"] = float(datos.get("P_cald_kPa", st.session_state["P_cald"]))
                        st.session_state["T_max"] = float(datos.get("T_max_C", st.session_state["T_max"]))
                        st.session_state["P_cond"] = float(datos.get("P_cond_kPa", st.session_state["P_cond"]))
                        st.session_state["tiene_recal"] = bool(datos.get("tiene_recal", False))
                        if datos.get("P_recal_kPa"):
                            st.session_state["P_recal"] = float(datos.get("P_recal_kPa"))
                        if datos.get("T_recal_C"):
                            st.session_state["T_recal"] = float(datos.get("T_recal_C"))
                        
                        fwh_lista = datos.get("fwh_lista", [])
                        st.session_state["num_fwh"] = len(fwh_lista)
                        st.session_state["fwh_data"] = [
                            {"tipo": f.get("tipo", "Abierto (Open)"), "presion": float(f.get("presion_kPa", 1000.0))}
                            for f in fwh_lista
                        ]
                        st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                        st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                        st.session_state["TH"] = float(datos.get("TH_K", 800.0))
                        st.session_state["T0"] = float(datos.get("T0_K", 300.0))
                        st.session_state["solucion_texto"] = datos.get("respuestas_directas", "")
                        st.success("¡Parámetros del problema extraídos!")
                        st.rerun()

# ==========================================
# BARRA LATERAL (ENTRADAS)
# ==========================================
st.sidebar.markdown("### ⚙️ Parámetros del Ciclo")

P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=100.0)
T_max = st.sidebar.number_input("Temperatura Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=5.0)

st.sidebar.markdown("---")
tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
if tiene_recal:
    P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=100.0)
    T_recal = st.sidebar.number_input("Temperatura Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)
else:
    P_recal, T_recal = 1000.0, 350.0

st.sidebar.markdown("---")
num_fwh = st.sidebar.number_input("Cantidad de Calentadores (FWH)", min_value=0, max_value=4, value=int(st.session_state["num_fwh"]))
fwh_configuracion = []
for i in range(num_fwh):
    st.sidebar.markdown(f"**Calentador #{i+1}:**")
    tipo_def = "Abierto (Open)"
    p_def = float(P_cald / (i + 2))
    if i < len(st.session_state["fwh_data"]):
        tipo_def = st.session_state["fwh_data"][i]["tipo"]
        p_def = float(st.session_state["fwh_data"][i]["presion"])
    tipo_sel = st.sidebar.selectbox(f"Tipo #{i+1}", ["Abierto (Open)", "Cerrado (Closed)"], index=0 if "Abierto" in tipo_def else 1, key=f"t_fwh_{i}")
    pres_sel = st.sidebar.number_input(f"Presión Extracción #{i+1} [kPa]", min_value=float(P_cond), max_value=float(P_cald), value=p_def, step=50.0, key=f"p_fwh_{i}")
    fwh_configuracion.append({"tipo": tipo_sel, "presion": pres_sel})

with st.sidebar.expander("Eficiencias y Entorno (2da Ley)"):
    eta_t = st.slider("Eficiencia Turbina (η_t) [%]", 50.0, 100.0, float(st.session_state["eta_t"]), 1.0) / 100.0
    eta_p = st.slider("Eficiencia Bomba (η_p) [%]", 50.0, 100.0, float(st.session_state["eta_p"]), 1.0) / 100.0
    TH = st.number_input("Temp. Fuente / Horno (T_H) [K]", value=float(st.session_state["TH"]), step=25.0)
    T0 = st.number_input("Temp. Ambiente / Sumidero (T_0) [K]", value=float(st.session_state["T0"]), step=5.0)

# ==========================================
# CÁLCULOS TERMODINÁMICOS REALES (CoolProp)
# ==========================================
fluido = 'Water'
P_cald_Pa = P_cald * 1e3
P_cond_Pa = P_cond * 1e3
T_max_K = T_max + 273.15
P_recal_Pa = P_recal * 1e3
T_recal_K = T_recal + 273.15

try:
    # Estado 1: Salida del condensador
    h1 = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

    # Entrada a Turbina de Alta Presión
    h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
    s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)

    if tiene_recal:
        h_rec_s = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        h_rec_sal = h_in_turb - eta_t * (h_in_turb - h_rec_s)
        s_rec_sal = CP.PropsSI('S', 'P', P_recal_Pa, 'H', h_rec_sal, fluido)
        T_rec_sal = CP.PropsSI('T', 'P', P_recal_Pa, 'H', h_rec_sal, fluido) - 273.15

        h_rec_in2 = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
        s_rec_in2 = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)

        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_rec_in2, fluido)
        h_out_turb = h_rec_in2 - eta_t * (h_rec_in2 - h_out_s)
        w_t = (h_in_turb - h_rec_sal) + (h_rec_in2 - h_out_turb)
        q_recal = h_rec_in2 - h_rec_sal
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = CP.PropsSI('T', 'P', P_cond_Pa, 'H', h_out_turb, fluido) - 273.15
    else:
        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_in_turb, fluido)
        h_out_turb = h_in_turb - eta_t * (h_in_turb - h_out_s)
        w_t = h_in_turb - h_out_turb
        q_recal = 0.0
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = CP.PropsSI('T', 'P', P_cond_Pa, 'H', h_out_turb, fluido) - 273.15

    w_b = v1 * (P_cald_Pa - P_cond_Pa) / eta_p
    h2 = h1 + w_b
    s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
    T2 = CP.PropsSI('T', 'P', P_cald_Pa, 'H', h2, fluido) - 273.15

    q_in = (h_in_turb - h2) + q_recal
    q_out = h_out_turb - h1
    w_neto = w_t - w_b
    eta_th = (w_neto / q_in) * 100.0

    w_rev = q_in * (1.0 - (T0 / TH))
    eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    # =========================================================
    # 1. DIAGRAMA T-s PROFESIONAL (ESTILO LIBRO DE ÇENGEL)
    # =========================================================
    st.markdown('<div class="section-header">📈 Diagrama Temperatura - Entropía (T-s)</div>', unsafe_allow_html=True)
    
    T_crit = CP.PropsSI('Tcrit', fluido)
    T_rango = np.linspace(274.15, T_crit - 0.5, 250)
    S_liq = np.array([CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango])
    S_vap = np.array([CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango])

    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=130)

    # Campana de saturación estilo libro
    ax.plot(S_liq, T_rango - 273.15, color='#1e293b', linewidth=2.2)
    ax.plot(S_vap, T_rango - 273.15, color='#1e293b', linewidth=2.2)

    # Isóbaras del sistema
    def trazar_isobara(P_val, color_linea='#94a3b8', label_txt=''):
        T_sat = CP.PropsSI('T', 'P', P_val, 'Q', 0, fluido) - 273.15
        s_f = CP.PropsSI('S', 'P', P_val, 'Q', 0, fluido)/1e3
        s_g = CP.PropsSI('S', 'P', P_val, 'Q', 1, fluido)/1e3
        
        # Línea horizontal en zona de mezcla
        ax.plot([s_f, s_g], [T_sat, T_sat], color=color_linea, linestyle='-', linewidth=1.2, alpha=0.85)
        # Curva de vapor sobrecalentado
        T_sup = np.linspace(T_sat, min(650.0, T_max + 30.0), 40)
        s_sup = [CP.PropsSI('S', 'P', P_val, 'T', t + 273.15, fluido)/1e3 for t in T_sup]
        ax.plot(s_sup, T_sup, color=color_linea, linestyle='-', linewidth=1.2, alpha=0.85)
        
        if label_txt:
            ax.text(s_sup[int(len(s_sup)*0.45)], T_sup[int(len(T_sup)*0.45)] + 10, label_txt, 
                    fontsize=9, color='#334155', fontweight='600',
                    bbox=dict(boxstyle='square,pad=0.15', facecolor='white', edgecolor='none', alpha=0.7))

    trazar_isobara(P_cond_Pa, '#cbd5e1', f'{P_cond/1e3:.2f} MPa' if P_cond>=1000 else f'{P_cond:.0f} kPa')
    if tiene_recal:
        trazar_isobara(P_recal_Pa, '#94a3b8', f'{P_recal/1e3:.1f} MPa')
    for f in fwh_configuracion:
        trazar_isobara(f['presion']*1e3, '#cbd5e1', f"{f['presion']/1e3:.2f} MPa" if f['presion']>=1000 else f"{f['presion']:.1f} kPa")
    trazar_isobara(P_cald_Pa, '#64748b', f'{P_cald/1e3:.1f} MPa')

    # Trazo del ciclo termodinámico y estados numerados
    if tiene_recal and num_fwh >= 2:
        # Puntos del ciclo idéntico al Ejemplo 10-6 del Çengel
        h_6_p = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        s_6_p = s_in_turb
        T_6_p = CP.PropsSI('T', 'P', P_recal_Pa, 'H', h_6_p, fluido) - 273.15

        p_fwh_abierto = min(f['presion'] for f in fwh_configuracion) * 1e3
        h_8_p = CP.PropsSI('H', 'P', p_fwh_abierto, 'S', s_rec_in2, fluido)
        s_8_p = s_rec_in2
        T_8_p = CP.PropsSI('T', 'P', p_fwh_abierto, 'H', h_8_p, fluido) - 273.15

        # Puntos con coordenadas (s, T)
        pt_9 = (s_in_turb/1e3, T_max)
        pt_10 = (s_6_p/1e3, T_6_p)
        pt_11 = (s_rec_in2/1e3, T_recal)
        pt_12 = (s_8_p/1e3, T_8_p)
        pt_13 = (s_out_turb/1e3, T_out_turb)
        pt_1 = (s1/1e3, T1)
        pt_2 = (s1/1e3, T1 + 8)
        pt_3 = (CP.PropsSI('S', 'P', p_fwh_abierto, 'Q', 0, fluido)/1e3, CP.PropsSI('T', 'P', p_fwh_abierto, 'Q', 0, fluido) - 273.15)
        pt_4 = (pt_3[0], pt_3[1] + 12)
        pt_6 = (CP.PropsSI('S', 'P', P_recal_Pa, 'Q', 0, fluido)/1e3, CP.PropsSI('T', 'P', P_recal_Pa, 'Q', 0, fluido) - 273.15)
        pt_7 = (pt_6[0], pt_6[1] + 10)
        pt_5 = (pt_6[0] - 0.25, pt_6[1] - 8)
        pt_8 = (pt_6[0] - 0.12, pt_6[1] + 3)

        # Conectar líneas del ciclo
        ax.plot([pt_9[0], pt_10[0]], [pt_9[1], pt_10[1]], color='#2563eb', linewidth=2.4)
        ax.plot([pt_10[0], pt_11[0]], [pt_10[1], pt_11[1]], color='#dc2626', linewidth=2.4)
        ax.plot([pt_11[0], pt_12[0], pt_13[0]], [pt_11[1], pt_12[1], pt_13[1]], color='#2563eb', linewidth=2.4)
        ax.plot([pt_13[0], pt_1[0]], [pt_13[1], pt_1[1]], color='#0284c7', linewidth=2.4)
        ax.plot([pt_1[0], pt_2[0], pt_3[0], pt_4[0], pt_5[0], pt_8[0], pt_7[0], pt_9[0]], 
                [pt_1[1], pt_2[1], pt_3[1], pt_4[1], pt_5[1], pt_8[1], pt_7[1], pt_9[1]], 
                color='#16a34a', linewidth=2.4)
        ax.plot([pt_10[0], pt_6[0], pt_7[0]], [pt_10[1], pt_6[1], pt_7[1]], color='#9333ea', linewidth=2.0)
        ax.plot([pt_12[0], pt_3[0]], [pt_12[1], pt_3[1]], color='#9333ea', linewidth=2.0)

        # Rotular estados con círculos negros y texto numerado
        estados = [
            (pt_1, "1"), (pt_2, "2"), (pt_3, "3"), (pt_4, "4"), (pt_5, "5"),
            (pt_6, "6"), (pt_7, "7"), (pt_8, "8"), (pt_9, "9"), (pt_10, "10"),
            (pt_11, "11"), (pt_12, "12"), (pt_13, "13")
        ]
        for coord, txt in estados:
            ax.plot(coord[0], coord[1], 'ko', markersize=4.8)
            ax.annotate(txt, xy=coord, xytext=(5, 4), textcoords='offset points', 
                        fontsize=9.5, fontweight='bold', color='#0f172a')

        # Etiquetas de fracciones de flujo
        ax.text(6.0, 520, '1 kg', fontsize=9, color='#1e293b', fontstyle='italic')
        ax.text(6.8, 520, '1 - y', fontsize=9, color='#1e293b', fontstyle='italic')
        ax.text(6.85, 360, 'y', fontsize=9, color='#7c3aed', fontweight='600')
        ax.text(7.45, 230, 'z', fontsize=9, color='#7c3aed', fontweight='600')
        ax.text(7.48, 140, '1 - y - z', fontsize=9, color='#1e293b', fontstyle='italic')

    else:
        # Ciclo con recalentamiento o simple
        if tiene_recal:
            pts_s = [s1/1e3, s2/1e3, s_in_turb/1e3, s_rec_sal/1e3, s_rec_in2/1e3, s_out_turb/1e3, s1/1e3]
            pts_t = [T1, T2, T_max, T_rec_sal, T_recal, T_out_turb, T1]
            labels = ["1", "2", "3", "4", "5", "6"]
        else:
            pts_s = [s1/1e3, s2/1e3, s_in_turb/1e3, s_out_turb/1e3, s1/1e3]
            pts_t = [T1, T2, T_max, T_out_turb, T1]
            labels = ["1", "2", "3", "4"]

        ax.plot(pts_s, pts_t, color='#2563eb', marker='o', markersize=5, linewidth=2.2, label='Trayectoria del Ciclo')
        for i, lbl in enumerate(labels):
            ax.annotate(lbl, xy=(pts_s[i], pts_t[i]), xytext=(5, 5), textcoords='offset points', 
                        fontsize=10, fontweight='bold', color='#0f172a')

    ax.set_xlabel("Entropía, s [kJ/kg · K]", fontsize=10, fontweight='500', color='#1e293b')
    ax.set_ylabel("Temperatura, T [°C]", fontsize=10, fontweight='500', color='#1e293b')
    ax.set_xlim(0.0, 9.2)
    ax.set_ylim(-10, max(680.0, T_max + 50.0))
    ax.grid(True, linestyle=':', alpha=0.5, color='#cbd5e1')
    
    # Ejes limpios estilo publicación
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#334155')
        ax.spines[spine].set_linewidth(1.3)
    ax.spines['left'].set_position(('outward', 6))
    ax.spines['bottom'].set_position(('outward', 6))

    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    st.pyplot(fig)

    # =========================================================
    # 2. TARJETAS DE RESULTADOS CLAVE
    # =========================================================
    st.markdown('<div class="section-header">📊 Resumen Ejecutivo del Ciclo</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Eficiencia Térmica (η_th)", f"{eta_th:.2f} %")
    m2.metric("Eficiencia 2da Ley (η_II)", f"{eta_II:.2f} %")
    m3.metric("Trabajo Neto (W_neto)", f"{w_neto/1e3:.2f} kJ/kg")
    m4.metric("Calor Entrada (Qin)", f"{q_in/1e3:.2f} kJ/kg")

    # =========================================================
    # 3. TABLA DE ESTADOS Y DETALLES TÉCNICOS
    # =========================================================
    col_t1, col_t2 = st.columns([1.3, 1.0])
    with col_t1:
        st.markdown('<div class="section-header">📋 Estados Termodinámicos Calculados</div>', unsafe_allow_html=True)
        filas = [
            {"Estado": "1 (Salida Condensador)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T1:.1f}", "h [kJ/kg]": f"{h1/1e3:.2f}", "s [kJ/kg·K]": f"{s1/1e3:.4f}"},
            {"Estado": "2 (Salida Bomba Principal)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
            {"Estado": "Entrada Turbina AP", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h_in_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_in_turb/1e3:.4f}"},
            {"Estado": "Salida Turbina / Condensador", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_out_turb:.1f}", "h [kJ/kg]": f"{h_out_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_out_turb/1e3:.4f}"}
        ]
        st.dataframe(filas, use_container_width=True, hide_index=True)

    with col_t2:
        if num_fwh > 0:
            st.markdown('<div class="section-header">♻️ Calentadores FWH Activos</div>', unsafe_allow_html=True)
            t_fwh = []
            for idx, c in enumerate(fwh_configuracion):
                t_fwh.append({
                    "Calentador": f"FWH #{idx+1}",
                    "Tipo": c["tipo"],
                    "P [kPa]": f"{c['presion']:.0f}",
                    "P [MPa]": f"{(c['presion']/1000.0):.2f}"
                })
            st.dataframe(t_fwh, use_container_width=True, hide_index=True)

    # =========================================================
    # 4. SOLUCIÓN COMPLETA DE LOS INCISOS (AL FINAL DE LA PÁGINA)
    # =========================================================
    if st.session_state["solucion_texto"]:
        st.markdown('<div class="section-header">📝 Respuestas Detalladas del Problema (Incisos)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="solution-box">{st.session_state["solucion_texto"]}</div>', unsafe_allow_html=True)

except Exception as err:
    st.error(f"Error procesando propiedades en CoolProp: {err}")
