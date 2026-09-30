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
    page_title="TermoRankine Pro | Centrales de Potencia & Cogeneración",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    /* Ocultar el menú superior y el footer por defecto de Streamlit para que parezca una app real */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Fondo global oscuro y moderno */
    .stApp {
        background-color: #0b0f19;
        background-image: radial-gradient(circle at 50% 0%, #1a2235 0%, #0b0f19 70%);
    }

    /* Títulos con gradiente estilo Apple/Awwwards */
    .gradient-text {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 20px;
    }

    /* Tarjetas estilo Glassmorphism (Cristal) para la Memoria de Cálculo */
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

    /* Animación al pasar el mouse (Hover) */
    .glass-card:hover {
        transform: translateY(-5px);
        border: 1px solid rgba(79, 172, 254, 0.3);
        box-shadow: 0 10px 40px rgba(0, 242, 254, 0.1);
    }

    /* Estilo para los números y resultados destacados */
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
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-title">⚡ TermoRankine Pro</div>
    <div class="hero-sub">Simulador térmico integral: ciclos de potencia regenerativos con trampas/bombas, cogeneración y diagramas T-s dinámicos.</div>
</div>
""", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b9eb7; font-size: 1.1rem; margin-top: -15px;'>Desarrollado por: Alberto Mendieta | Cédula: 6-728-80 | UTP Azuero</p>", unsafe_allow_html=True)


try:
    client = genai.Client(api_key=st.secrets["API_KEY"])
except Exception:
    client = None

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

metodo = st.sidebar.radio("Modo de ingreso:", ["✍️ Manual", "📷 Cargar Imagen / Enunciado"], horizontal=True)

if metodo == "📷 Cargar Imagen / Enunciado":
    archivo = st.sidebar.file_uploader("Subir diagrama o enunciado técnico", type=["png", "jpg", "jpeg", "webp"])
    if archivo and client:
        img = Image.open(archivo)
        if st.sidebar.button("🔍 Extraer Datos y Procesar", type="primary", use_container_width=True):
            with st.spinner("Digitalizando parámetros termodinámicos..."):
                try:
                    prompt = """
                    Analiza la imagen del ciclo térmico. Devuelve ÚNICAMENTE un JSON con:
                    {
                      "tipo_planta": "Central de Potencia" o "Cogeneracion",
                      "P_cald_kPa": float,
                      "T_max_C": float,
                      "P_cond_kPa": float,
                      "m_dot_kgs": float,
                      "tiene_recal": bool,
                      "P_recal_kPa": float o null,
                      "T_recal_C": float o null,
                      "num_fwh": int,
                      "P_proc_kPa": float o null,
                      "frac_byp": float o null,
                      "frac_turb_proc": float o null
                    }
                    Reglas: presiones en kPa (ej: 15 MPa = 15000, 7 MPa = 7000, 500 kPa = 500, 10 kPa = 10).
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
                    st.session_state["m_dot"] = float(datos.get("m_dot_kgs", st.session_state["m_dot"]))
                    st.session_state["tiene_recal"] = bool(datos.get("tiene_recal", False))
                    if datos.get("P_recal_kPa"):
                        st.session_state["P_recal"] = float(datos.get("P_recal_kPa"))
                    if datos.get("T_recal_C"):
                        st.session_state["T_recal"] = float(datos.get("T_recal_C"))
                    if datos.get("P_proc_kPa"):
                        st.session_state["P_proc"] = float(datos.get("P_proc_kPa"))
                        st.session_state["tipo_planta"] = "Planta de Cogeneración (Calor y Potencia)"
                    st.sidebar.success("¡Parámetros cargados!")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error procesando imagen: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Fronteras Térmicas Principales:**")
P_cald = st.sidebar.number_input("Presión Caldera [kPa]", value=float(st.session_state["P_cald"]), step=500.0)
T_max = st.sidebar.number_input("Temperatura Entrada Turbina [°C]", value=float(st.session_state["T_max"]), step=10.0)
P_cond = st.sidebar.number_input("Presión Condensador [kPa]", value=float(st.session_state["P_cond"]), step=1.0)
m_dot = st.sidebar.number_input("Flujo Másico Total (ṁ) [kg/s]", value=float(st.session_state["m_dot"]), step=1.0)

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
        
        # Selector dinámico: Trampa de Vapor vs Bomba de Drenaje
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
        h_cond_out = CP.PropsSI('H', 'P', P_cond_Pa, 'Q', 0, fluido)
        s_cond_out = CP.PropsSI('S', 'P', P_cond_Pa, 'Q', 0, fluido)
        v_cond = 1 / CP.PropsSI('D', 'P', P_cond_Pa, 'Q', 0, fluido)
        T_cond_out = CP.PropsSI('T', 'P', P_cond_Pa, 'Q', 0, fluido) - 273.15

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

        # Cálculo de bombas considerando si hay bombas de drenaje activas
        fwh_con_bomba = [f for f in fwh_configuracion if "Bomba" in f.get("drenaje", "")]
        w_b_principal = v_cond * (P_cald_Pa - P_cond_Pa) / eta_p
        
        # Trabajo adicional por bombas de drenaje
        w_b_drenajes = 0.0
        for f in fwh_con_bomba:
            p_f_pa = f['presion'] * 1e3
            vf_f = 1 / CP.PropsSI('D', 'P', p_f_pa, 'Q', 0, fluido)
            w_b_drenajes += 0.08 * (vf_f * (P_cald_Pa - p_f_pa) / eta_p)

        w_b_total = w_b_principal + w_b_drenajes
        h2 = h_cond_out + w_b_principal
        s2 = CP.PropsSI('S', 'P', P_cald_Pa, 'H', h2, fluido)
        T2 = get_T_safe(P_cald_Pa, h2)

        q_in = (h_in_turb - h2) + q_recal
        w_neto = w_t - w_b_total
        W_dot_neto = (m_dot * w_neto) / 1e3
        Q_dot_in = (m_dot * q_in) / 1e3
        Q_dot_proc = 0.0
        eps_u = (w_neto / q_in) * 100.0
        eta_th = eps_u
        w_rev = q_in * (1.0 - (T0 / TH))
        eta_II = (w_neto / w_rev) * 100.0 if w_rev > 0 else 0.0

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
    tab_ts, tab_estados, tab_procedimiento = st.tabs([
        "📈 Diagrama T-s Interactivo", 
        "📋 Estados Termodinámicos", 
        "📝 Memoria de Cálculo"
    ])

    with tab_ts:
        T_crit = CP.PropsSI('Tcrit', fluido)
        T_campana = np.linspace(273.16, T_crit - 0.2, 250)
        s_liq = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
        s_vap = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

        fig = go.Figure()

        # Campana de saturación
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

        # Diagrama para Cogeneración
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

        # Diagrama para Potencia Regenerativa con Trampas / Bombas
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

                # Trazado visual de la extracción
                fig.add_trace(go.Scatter(
                    x=x_ext, y=y_ext, mode='lines',
                    line=dict(color=color_ciclo, width=1.8, dash='solid'),
                    name=f'Extracción {fmt_p(p_pa/1000)}',
                    hoverinfo='skip'
                ))

                # Si es calentador cerrado con trampa de vapor: trazo de estrangulamiento
                if "Trampa" in f['drenaje']:
                    p_inferior = fwh_ord[idx+1]['presion']*1e3 if idx+1 < len(fwh_ord) else P_cond_Pa
                    t_inferior = CP.PropsSI('T', 'P', p_inferior, 'Q', 0, fluido) - 273.15
                    s_sf_inf = CP.PropsSI('S', 'P', p_inferior, 'Q', 0, fluido) / 1e3
                    
                    # Línea discontinua que muestra el vapor flash y condensado cayendo en cascada
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
                {"Estado": "Salida Bomba Principal (2)", "P [kPa]": f"{P_cald:.1f}", "T [°C]": f"{T2:.1f}", "h [kJ/kg]": f"{h2/1e3:.2f}", "s [kJ/kg·K]": f"{s2/1e3:.4f}"},
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
