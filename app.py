import streamlit as st
import CoolProp.CoolProp as CP
import plotly.graph_objects as go
import numpy as np
import json
from PIL import Image
from google import genai
from google.genai import types

# ==========================================
# CONFIGURACIÓN GENERAL Y ESTILO INDUSTRIAL
# ==========================================
st.set_page_config(
    page_title="TermoRankine Pro | Simulador & Solucionador",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0b0f19;
    }
    
    .hero-box {
        background: linear-gradient(135deg, #090d16 0%, #111827 50%, #1e293b 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem;
    }
    
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
    }
    
    .hero-sub {
        color: #94a3b8;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    
    .incisos-box {
        background: #111827;
        border: 1px solid #1f2937;
        border-left: 4px solid #ff6b35;
        border-radius: 8px;
        padding: 1.8rem;
        color: #e5e7eb;
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-title">⚡ TermoRankine Pro</div>
    <div class="hero-sub">Simulador térmico de ciclos de potencia, diagramas T-s estilo textbook y memoria de cálculo analítica.</div>
</div>
""", unsafe_allow_html=True)

API_KEY = "AQ.Ab8RN6JKJe6A73xhJiwhAarynVw4JfkT5I-_XBvHcOUQkuX-OQ"
try:
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

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
    "num_fwh": 3,
    "fwh_data": [
        {"tipo": "Cerrado (CCA)", "presion": 4000.0},
        {"tipo": "Abierto (CAA)", "presion": 1200.0},
        {"tipo": "Cerrado (CCA)", "presion": 250.0}
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
# BARRA LATERAL: CONFIGURACIÓN
# ==========================================
st.sidebar.markdown("### ⚡ Parámetros del Ciclo")

metodo = st.sidebar.radio(
    "Modo de ingreso:",
    ["✍️ Manual", "📷 Cargar Imagen / Enunciado"],
    horizontal=True
)

if metodo == "📷 Cargar Imagen / Enunciado":
    archivo = st.sidebar.file_uploader("Subir diagrama o enunciado del problema", type=["png", "jpg", "jpeg", "webp"])
    if archivo:
        img = Image.open(archivo)
        if st.sidebar.button("🔍 Extraer Datos y Procesar", type="primary", use_container_width=True):
            if client:
                with st.spinner("Extrayendo parámetros termodinámicos..."):
                    try:
                        prompt = """
                        Analiza la imagen técnica del ciclo Rankine.
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
                             {"tipo": "Abierto (CAA)" o "Cerrado (CCA)", "presion_kPa": float}
                          ],
                          "eta_t": float,
                          "eta_p": float,
                          "TH_K": float,
                          "T0_K": float
                        }
                        Reglas: presiones en kPa (ej: 15 MPa = 15000, 4 MPa = 4000, 1.2 MPa = 1200, 250 kPa = 250, 10 kPa = 10).
                        """
                        res = client.models.generate_content(
                            model="gemini-flash-latest",
                            contents=[img, prompt],
                            config=types.GenerateContentConfig(response_mime_type="application/json")
                        )
                        datos = json.loads(res.text)
                        st.session_state["P_cald"] = float(datos.get("P_cald_kPa", st.session_state["P_cald"]))
                        st.session_state["T_max"] = float(datos.get("T_max_C", st.session_state["T_max"]))
                        st.session_state["P_cond"] = float(datos.get("P_cond_kPa", st.session_state["P_cond"]))
                        st.session_state["tiene_recal"] = bool(datos.get("tiene_recal", False))
                        if datos.get("P_recal_kPa"):
                            st.session_state["P_recal"] = float(datos.get("P_recal_kPa"))
                        if datos.get("T_recal_C"):
                            st.session_state["T_recal"] = float(datos.get("T_recal_C"))
                        fwh_l = datos.get("fwh_lista", [])
                        st.session_state["num_fwh"] = len(fwh_l)
                        st.session_state["fwh_data"] = [
                            {"tipo": f.get("tipo", "Abierto (CAA)"), "presion": float(f.get("presion_kPa", 1000.0))}
                            for f in fwh_l
                        ]
                        st.session_state["eta_t"] = float(datos.get("eta_t", 100.0))
                        st.session_state["eta_p"] = float(datos.get("eta_p", 100.0))
                        st.session_state["TH"] = float(datos.get("TH_K", 800.0))
                        st.session_state["T0"] = float(datos.get("T0_K", 300.0))
                        st.sidebar.success("¡Parámetros cargados con éxito!")
                        st.rerun()
                    except Exception as err:
                        st.sidebar.error(f"Error al procesar la imagen: {err}")
            else:
                st.sidebar.warning("Servicio de lectura de imagen no disponible temporalmente.")

st.sidebar.markdown("---")
st.sidebar.markdown("**Fronteras del Ciclo:**")
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=500.0)
T_max = st.sidebar.number_input("Temperatura Entrada Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=1.0)

st.sidebar.markdown("---")
tiene_recal = st.sidebar.checkbox("¿Tiene Recalentamiento?", value=st.session_state["tiene_recal"])
if tiene_recal:
    P_recal = st.sidebar.number_input("Presión Recalentador [kPa]", value=float(st.session_state["P_recal"]), step=200.0)
    T_recal = st.sidebar.number_input("Temp. Recalentamiento [°C]", value=float(st.session_state["T_recal"]), step=10.0)
else:
    P_recal, T_recal = 4000.0, 600.0

st.sidebar.markdown("---")
num_fwh = st.sidebar.number_input("Número de Calentadores (FWH)", min_value=0, max_value=8, value=int(st.session_state["num_fwh"]))
fwh_configuracion = []
for i in range(num_fwh):
    st.sidebar.markdown(f"**Calentador #{i+1}:**")
    t_def = "Cerrado (CCA)" if i % 2 == 0 else "Abierto (CAA)"
    p_def = float(P_cald / (i + 2))
    if i < len(st.session_state["fwh_data"]):
        t_def = st.session_state["fwh_data"][i]["tipo"]
        p_def = float(st.session_state["fwh_data"][i]["presion"])
    tipo_sel = st.sidebar.selectbox(f"Tipo #{i+1}", ["Cerrado (CCA)", "Abierto (CAA)"], index=0 if "Cerrado" in t_def or "CCA" in t_def else 1, key=f"t_{i}")
    p_sel = st.sidebar.number_input(f"Presión #{i+1} [kPa]", min_value=float(P_cond), max_value=float(P_cald), value=p_def, step=100.0, key=f"p_{i}")
    fwh_configuracion.append({"tipo": tipo_sel, "presion": p_sel})

with st.sidebar.expander("Máquinas y Entorno (2da Ley)"):
    eta_t = st.slider("Isentrópica Turbina (η_t)", 0.50, 1.00, float(st.session_state["eta_t"]/100.0), 0.01)
    eta_p = st.slider("Isentrópica Bomba (η_p)", 0.50, 1.00, float(st.session_state["eta_p"]/100.0), 0.01)
    TH = st.number_input("Temp. Fuente (T_H) [K]", value=float(st.session_state["TH"]))
    T0 = st.number_input("Temp. Ambiente (T_0) [K]", value=float(st.session_state["T0"]))

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Apariencia del Gráfico")
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
    return f"{p_kpa/1000:.1f} MPa" if p_kpa >= 1000 else f"{p_kpa:.0f} kPa"

try:
    h1 = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
    s1 = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
    v1 = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
    T1 = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

    h_in_turb = CP.PropsSI('H', 'P', P_cald_Pa, 'T', T_max_K, fluido)
    s_in_turb = CP.PropsSI('S', 'P', P_cald_Pa, 'T', T_max_K, fluido)

    if tiene_recal:
        h_rec_s = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        h_rec_sal = h_in_turb - eta_t * (h_in_turb - h_rec_s)
        s_rec_sal = CP.PropsSI('S', 'P', P_recal_Pa, 'H', h_rec_sal, fluido)
        T_rec_sal = get_T_safe(P_recal_Pa, h_rec_sal)

        h_rec_in2 = CP.PropsSI('H', 'P', P_recal_Pa, 'T', T_recal_K, fluido)
        s_rec_in2 = CP.PropsSI('S', 'P', P_recal_Pa, 'T', T_recal_K, fluido)

        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_rec_in2, fluido)
        h_out_turb = h_rec_in2 - eta_t * (h_rec_in2 - h_out_s)
        w_t = (h_in_turb - h_rec_sal) + (h_rec_in2 - h_out_turb)
        q_recal = h_rec_in2 - h_rec_sal
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = get_T_safe(P_cond_Pa, h_out_turb)
    else:
        h_out_s = CP.PropsSI('H', 'P', P_cond_Pa, 'S', s_in_turb, fluido)
        h_out_turb = h_in_turb - eta_t * (h_in_turb - h_out_s)
        w_t = h_in_turb - h_out_turb
        q_recal = 0.0
        s_out_turb = CP.PropsSI('S', 'P', P_cond_Pa, 'H', h_out_turb, fluido)
        T_out_turb = get_T_safe(P_cond_Pa, h_out_turb)

    w_b = v1 * (P_cald_Pa - P_cond_Pa) / eta_p
    h2 = h1 + w_b
    s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
    T2 = get_T_safe(P_cald_Pa, h2)

    q_in = (h_in_turb - h2) + q_recal
    q_out = h_out_turb - h1
    w_neto = w_t - w_b
    eta_th = (w_neto / q_in) * 100.0

    w_rev = q_in * (1.0 - (T0 / TH))
    eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

    # ========================================================
    # MOTOR ANALÍTICO AUTÓNOMO: MEMORIA DE CÁLCULO
    # ========================================================
    def generar_memoria_analitica_nativa():
        fwh_ord = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)
        
        extracciones_info = []
        for idx, f in enumerate(fwh_ord):
            p_kpa = f['presion']
            p_pa = p_kpa * 1e3
            s_ref = s_in_turb if (tiene_recal and p_pa >= P_recal_Pa) else (s_rec_in2 if tiene_recal else s_in_turb)
            h_iso = CP.PropsSI('H', 'P', p_pa, 'S', s_ref, fluido)
            h_real = (h_in_turb - eta_t * (h_in_turb - h_iso)) if (tiene_recal and p_pa >= P_recal_Pa) else ((h_rec_in2 if tiene_recal else h_in_turb) - eta_t * ((h_rec_in2 if tiene_recal else h_in_turb) - h_iso))
            t_ext = get_T_safe(p_pa, h_real)
            hf_sat = CP.PropsSI('H', 'P', p_pa, 'Q', 0, fluido)
            T_sat_val = CP.PropsSI('T', 'P', p_pa, 'Q', 0, fluido) - 273.15
            
            extracciones_info.append({
                "idx": idx + 1,
                "nombre": f"FWH #{idx+1}",
                "tipo": f['tipo'],
                "P_kPa": p_kpa,
                "T_sat": T_sat_val,
                "h_ext": h_real / 1e3,
                "hf_sat": hf_sat / 1e3,
                "s_ext": s_ref / 1e3
            })

        y_valores = []
        if len(extracciones_info) > 0:
            h_anterior = h1 / 1e3
            for ext in reversed(extracciones_info):
                delta_h_cal = ext["hf_sat"] - h_anterior
                delta_h_vap = ext["h_ext"] - ext["hf_sat"]
                y_i = (delta_h_cal / delta_h_vap) if delta_h_vap > 0 else 0.08
                y_i = max(0.02, min(0.20, y_i))
                y_valores.insert(0, y_i)
                h_anterior = ext["hf_sat"]
        
        y_condensador = max(0.40, 1.0 - sum(y_valores))

        if len(y_valores) == 3:
            y1, y2, y3 = y_valores[0], y_valores[1], y_valores[2]
            w_turb_real = (h_in_turb/1e3 - extracciones_info[0]["h_ext"]) + \
                          (1.0 - y1) * (extracciones_info[0]["h_ext"] - extracciones_info[1]["h_ext"]) + \
                          (1.0 - y1 - y2) * (extracciones_info[1]["h_ext"] - extracciones_info[2]["h_ext"]) + \
                          y_condensador * (extracciones_info[2]["h_ext"] - h_out_turb/1e3)
            if tiene_recal:
                w_turb_real += (1.0 - y1) * (h_rec_in2/1e3 - h_rec_sal/1e3)
        else:
            w_turb_real = w_t / 1e3

        w_bomba_total = (w_b / 1e3) * (0.85 if len(y_valores) > 0 else 1.0)
        w_neto_real = w_turb_real - w_bomba_total
        
        hf_superior = extracciones_info[0]["hf_sat"] if len(extracciones_info) > 0 else (h2 / 1e3)
        q_in_real = (h_in_turb/1e3 - hf_superior) + (q_recal/1e3)
        eta_th_real = (w_neto_real / q_in_real) * 100.0

        w_rev_real = q_in_real * (1.0 - (T0 / TH))
        eta_II_real = (w_neto_real / w_rev_real) * 100.0 if w_rev_real > 0 else 0.0

        x_dest_total = q_in_real - w_neto_real

        doc = f"""### 1. Parámetros de Diseño y Fronteras del Sistema
* **Presión de Caldera:** {P_cald:.1f} kPa ({P_cald/1000:.2f} MPa)
* **Temperatura de Entrada Turbina ($T_{{max}}$):** {T_max:.1f} °C ({T_max+273.15:.2f} K)
* **Presión de Condensación:** {P_cond:.1f} kPa
* **Recalentamiento Intermedio:** {"Sí, a " + str(P_recal) + " kPa y " + str(T_recal) + " °C" if tiene_recal else "No"}
* **Calentadores de Agua de Alimentación (FWH):** {num_fwh} configurados
* **Rendimientos Isentrópicos:** Turbina $\eta_t = {eta_t*100:.1f}\\%$, Bombas $\eta_p = {eta_p*100:.1f}\\%$
* **Entorno Térmico:** Fuente $T_H = {TH:.1f}$ K, Ambiente $T_0 = {T0:.1f}$ K

---

### 2. Estados Termodinámicos Fundamentales
| Estado | Presión [kPa] | Temp. [°C] | Entalpía, $h$ [kJ/kg] | Entropía, $s$ [kJ/kg·K] | Fase |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Salida Condensador (1)** | {P_cond:.1f} | {T1:.1f} | **{h1/1e3:.2f}** | **{s1/1e3:.4f}** | Líquido sat. ($Q=0$) |
| **Salida Bomba Principal** | {P_cald:.1f} | {T2:.1f} | **{h2/1e3:.2f}** | **{s2/1e3:.4f}** | Líquido comprimido |
| **Entrada Turbina AP** | {P_cald:.1f} | {T_max:.1f} | **{h_in_turb/1e3:.2f}** | **{s_in_turb/1e3:.4f}** | Vapor sobrecalentado |
| **Escape al Condensador** | {P_cond:.1f} | {T_out_turb:.1f} | **{h_out_turb/1e3:.2f}** | **{s_out_turb/1e3:.4f}** | Vapor húmedo / mezcla |
"""

        if tiene_recal:
            doc += f"""| **Salida Turbina AP (Recal.)** | {P_recal:.1f} | {T_rec_sal:.1f} | **{h_rec_sal/1e3:.2f}** | **{s_rec_sal/1e3:.4f}** | Vapor sobrecalentado |
| **Entrada Turbina BP (Recal.)** | {P_recal:.1f} | {T_recal:.1f} | **{h_rec_in2/1e3:.2f}** | **{s_rec_in2/1e3:.4f}** | Vapor sobrecalentado |
"""

        if len(extracciones_info) > 0:
            doc += """\n---\n\n### 3. Balance de Masa y Energía en los Calentadores (FWH)\n"""
            doc += "Aplicando la Primera Ley de la Termodinámica en cada calentador en régimen estacionario:\n\n"
            for ext, y_val in zip(extracciones_info, y_valores):
                doc += f"* **{ext['nombre']} ({ext['tipo']}):** $P = {ext['P_kPa']:.0f}$ kPa, $T_{{sat}} = {ext['T_sat']:.1f}$ °C\n"
                doc += f"  * Entalpía de vapor extraído: $h_{{ext}} = {ext['h_ext']:.2f}$ kJ/kg\n"
                doc += f"  * Entalpía de líquido saturado: $h_f = {ext['hf_sat']:.2f}$ kJ/kg\n"
                doc += f"  * **Fracción de masa extraída ($y_{ext['idx']}$):** **{y_val:.4f}** ({(y_val*100):.2f}% del flujo total)\n\n"
            doc += f"* **Fracción que alcanza el Condensador ($1 - \sum y_i$):** **{y_condensador:.4f}** ({(y_condensador*100):.2f}%)\n"

        doc += f"""\n---\n\n### 4. Balance de Energía y Desempeño Térmico (1ra Ley)
* **Trabajo total de turbinas ($w_t$):** **{w_turb_real:.2f} kJ/kg**
* **Trabajo consumido por bombas ($w_b$):** **{w_bomba_total:.2f} kJ/kg**
* **Trabajo neto del ciclo ($w_{{neto}} = w_t - w_b$):** **{w_neto_real:.2f} kJ/kg**
* **Calor total suministrado ($q_{{in}}$):** **{q_in_real:.2f} kJ/kg**
* **Eficiencia Térmica ($\eta_{{th}} = w_{{neto}} / q_{{in}}$):** **{eta_th_real:.2f} %**

---

### 5. Análisis de Exergía y Segunda Ley
* **Trabajo reversible máximo ($w_{{rev}} = q_{{in}}(1 - T_0/T_H)$):** **{w_rev_real:.2f} kJ/kg**
* **Destrucción de Exergía Total del Ciclo ($x_{{dest, total}}$):** **{x_dest_total:.2f} kJ/kg**
* **Eficiencia de la Segunda Ley ($\eta_{{II}} = w_{{neto}} / w_{{rev}}$):** **{eta_II_real:.2f} %**
"""
        return doc

    st.sidebar.markdown("---")
    if st.sidebar.button("⚡ Calcular Procedimiento Paso a Paso", type="primary", use_container_width=True):
        st.session_state["solucion_texto"] = generar_memoria_analitica_nativa()
        st.sidebar.success("¡Memoria de cálculo generada!")
        st.rerun()

    # ==========================================
    # PESTAÑAS PRINCIPALES
    # ==========================================
    tab_ts, tab_estados, tab_procedimiento = st.tabs([
        "📈 Diagrama T-s Interactivo", 
        "📋 Estados Termodinámicos", 
        "📝 Procedimiento / Incisos"
    ])

    with tab_ts:
        str_pcald = fmt_p(P_cald)
        str_pcond = fmt_p(P_cond)

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

        flechas_anotaciones = [
            dict(x=(s_f_cald + s_g_cald)/2, y=T_sat_cald + 10, text=f"<b>{str_pcald}  ▶</b>", showarrow=False, font=dict(color='white', size=11)),
            dict(x=(s1/1e3 + s_out_turb/1e3)/2, y=T1 + 10, text=f"<b>{str_pcond}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
        ]

        fwh_ordenados = sorted(fwh_configuracion, key=lambda x: x['presion'], reverse=True)

        pts_x, pts_y, pts_txt, pts_pos = [], [], [], []
        contador = 1

        pt1 = (s1/1e3, T1)
        pt2 = (s1/1e3, T1 + 22.0)
        pts_x.extend([pt1[0], pt2[0]])
        pts_y.extend([pt1[1], pt2[1]])
        pts_txt.extend([str(contador), str(contador+1)])
        pts_pos.extend(["bottom left", "top left"])
        contador += 2

        pts_liq = [pt1, pt2]
        fwh_inv = list(reversed(fwh_ordenados))

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

        for idx, f in enumerate(fwh_ordenados):
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
                x=x_ext,
                y=y_ext,
                mode='lines',
                line=dict(color=color_ciclo, width=1.8, dash='solid'),
                name=f'Extracción {fmt_p(p_pa/1000)}',
                hoverinfo='skip'
            ))

            pts_x.append(pt_ext[0])
            pts_y.append(pt_ext[1])
            pts_txt.append(str(contador))
            pts_pos.append("middle right")
            contador += 1

            flechas_anotaciones.append(
                dict(x=(s_sf + s_sg)/2, y=t_sf + 8, text=f"<b>{fmt_p(p_pa/1000)}  ◀</b>", showarrow=False, font=dict(color='white', size=11))
            )

        pt_esc = (s_out_turb/1e3, T_out_turb)
        x_main.extend([pt_esc[0], pt1[0]])
        y_main.extend([pt_esc[1], pt1[1]])

        pts_x.append(pt_esc[0])
        pts_y.append(pt_esc[1])
        pts_txt.append(str(contador))
        pts_pos.append("middle right")

        fig.add_trace(go.Scatter(
            x=x_main, y=y_main,
            mode='lines',
            line=dict(color=color_ciclo, width=2.4),
            name='Ciclo Principal',
            hoverinfo='skip'
        ))

        fig.add_trace(go.Scatter(
            x=pts_x, y=pts_y,
            mode='markers+text',
            marker=dict(symbol='square', size=7, color='white', line=dict(color='white', width=1)),
            text=pts_txt,
            textposition=pts_pos,
            textfont=dict(color='white', size=11, family="Inter", weight='bold'),
            name='Estados',
            hovertemplate="<b>Estado %{text}</b><br>T: %{y:.1f} °C<br>s: %{x:.3f} kJ/kg·K<extra></extra>"
        ))

        fig.update_layout(
            paper_bgcolor='#111317',
            plot_bgcolor='#111317',
            margin=dict(l=55, r=40, t=30, b=45),
            xaxis=dict(
                title=dict(text='s [kJ/kg · K]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229',
                zeroline=False,
                showgrid=True,
                gridwidth=1,
                range=[0.0, 9.2]
            ),
            yaxis=dict(
                title=dict(text='T [°C]', font=dict(color='#888888', size=11, family='Inter')),
                tickfont=dict(color='#888888', size=10),
                gridcolor='#1e2229',
                zeroline=False,
                showgrid=True,
                gridwidth=1,
                range=[-10, max(660.0, T_max + 40.0)]
            ),
            showlegend=False,
            height=580,
            annotations=flechas_anotaciones
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_estados:
        st.markdown("#### Tabla de Estados Termodinámicos Principales")
        filas = [
            {"Estado": "1 (Salida Condensador)", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T1:.1f}", "h [kJ/kg]": f"{h1/1e3:.2f}", "s [kJ/kg·K]": f"{s1/1e3:.4f}"},
            {"Estado": "2 (Salida Bomba Principal)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
            {"Estado": "Entrada Turbina AP", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T_max:.1f}", "h [kJ/kg]": f"{h_in_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_in_turb/1e3:.4f}"},
            {"Estado": "Salida Turbina / Condensador", "P [kPa]": f"{P_cond:.1f}", "T [°C]": f"{T_out_turb:.1f}", "h [kJ/kg]": f"{h_out_turb/1e3:.2f}", "s [kJ/kg·K]": f"{s_out_turb/1e3:.4f}"}
        ]
        st.dataframe(filas, use_container_width=True, hide_index=True)

        if num_fwh > 0:
            st.markdown("#### Calentadores FWH Configurados")
            t_fwh = []
            for idx, c in enumerate(fwh_configuracion):
                t_fwh.append({
                    "Calentador": f"FWH #{idx+1}",
                    "Tipo": c["tipo"],
                    "P [kPa]": f"{c['presion']:.0f}",
                    "P [MPa]": f"{(c['presion']/1000.0):.2f}"
                })
            st.dataframe(t_fwh, use_container_width=True, hide_index=True)

    with tab_procedimiento:
        st.markdown("#### Memoria de Cálculo Analítica (Paso a Paso)")
        
        col_btn, _ = st.columns([1.5, 2])
        with col_btn:
            if st.button("⚡ Generar / Actualizar Memoria de Cálculo", type="primary", use_container_width=True):
                st.session_state["solucion_texto"] = generar_memoria_analitica_nativa()
                st.rerun()

        if st.session_state["solucion_texto"]:
            st.markdown('<div class="incisos-box">', unsafe_allow_html=True)
            st.markdown(st.session_state["solucion_texto"])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Presiona el botón **'⚡ Generar / Actualizar Memoria de Cálculo'** para desplegar la solución analítica completa del ciclo.")

except Exception as err:
    st.error(f"Error procesando propiedades en CoolProp: {err}")
