
import streamlit as st
import CoolProp.CoolProp as CP
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Simulador Ciclo Rankine", layout="wide")

st.title("⚡ Simulador Interactivo: Ciclo Rankine Regenerativo")
st.markdown("Herramienta de cálculo termodinámico con propiedades de agua vía `CoolProp`.")

# --- BARRA LATERAL: PARÁMETROS DE ENTRADA ---
st.sidebar.header("Parámetros del Ciclo")

P_cald_kPa = st.sidebar.number_input("Presión Caldera [kPa]", min_value=100.0, max_value=30000.0, value=15000.0, step=500.0)
T_max_C = st.sidebar.slider("Temperatura Entrada Turbina [°C]", min_value=100.0, max_value=800.0, value=600.0, step=10.0)
P_cond_kPa = st.sidebar.number_input("Presión Condensador [kPa]", min_value=1.0, max_value=500.0, value=10.0, step=1.0)

tipo_ciclo = st.sidebar.selectbox("Régimen de Operación", ["Ideal (100% isentrópico)", "Real"])
if tipo_ciclo == "Real":
    eta_t = st.sidebar.slider("Eficiencia Turbina (η_t)", 0.50, 1.00, 0.88, 0.01)
    eta_p = st.sidebar.slider("Eficiencia Bombas (η_p)", 0.50, 1.00, 0.85, 0.01)
else:
    eta_t = 1.0
    eta_p = 1.0

st.sidebar.markdown("---")
# SELECTOR EXPLÍCITO DE CANTIDAD
num_fwh = st.sidebar.number_input("Cantidad de Calentadores (FWH)", min_value=0, max_value=8, value=2, step=1)

P_exts_kPa = []
default_pressures = [4000.0, 500.0, 200.0, 100.0, 50.0, 30.0, 20.0, 15.0]

for i in range(num_fwh):
    def_val = default_pressures[i] if i < len(default_pressures) else 100.0
    p_val = st.sidebar.number_input(
        f"Presión FWH #{i+1} [kPa]", 
        min_value=float(P_cond_kPa), 
        max_value=float(P_cald_kPa), 
        value=float(def_val), 
        step=50.0,
        key=f"fwh_{i}"
    )
    P_exts_kPa.append(p_val)

# --- CÁLCULO TERMODINÁMICO ---
fluido = 'Water'
P_cald = P_cald_kPa * 1e3
P_cond = P_cond_kPa * 1e3
T_max = T_max_C + 273.15
P_exts = [p * 1e3 for p in sorted(P_exts_kPa, reverse=True)]
N_fwh = len(P_exts)

# Turbina
h_in = CP.PropsSI('H', 'P', P_cald, 'T', T_max, fluido)
s_in = CP.PropsSI('S', 'P', P_cald, 'T', T_max, fluido)

h_vapor = []
for P_ext in P_exts:
    h_s = CP.PropsSI('H', 'P', P_ext, 'S', s_in, fluido)
    h_real = h_in - eta_t * (h_in - h_s)
    h_vapor.append(h_real)

h_out_s = CP.PropsSI('H', 'P', P_cond, 'S', s_in, fluido)
h_out_real = h_in - eta_t * (h_in - h_out_s)
T_out = CP.PropsSI('T', 'P', P_cond, 'H', h_out_real, fluido) - 273.15
s_out_real = CP.PropsSI('S', 'P', P_cond, 'H', h_out_real, fluido)

# Bombas y FWH
h_liq_actual = CP.PropsSI('H', 'P', P_cond, 'Q', 0, fluido)
v_liq = 1 / CP.PropsSI('D', 'P', P_cond, 'Q', 0, fluido)
P_actual = P_cond

h_liq_entradas, h_liq_salidas, w_bombas_esp = [], [], []
for P_ext in reversed(P_exts):
    w_b = v_liq * (P_ext - P_actual) / eta_p
    w_bombas_esp.append(w_b)
    h_liq_entradas.append(h_liq_actual + w_b)
    h_liq_actual = CP.PropsSI('H', 'P', P_ext, 'Q', 0, fluido)
    h_liq_salidas.append(h_liq_actual)
    v_liq = 1 / CP.PropsSI('D', 'P', P_ext, 'Q', 0, fluido)
    P_actual = P_ext

h_liq_entradas.reverse(); h_liq_salidas.reverse(); w_bombas_esp.reverse()
w_b_final = v_liq * (P_cald - P_actual) / eta_p
h_in_caldera = h_liq_actual + w_b_final
w_bombas_esp.insert(0, w_b_final)

# Balance de Masa
y_frac = []
flujo_masa = 1.0
flujos_bomba = [1.0]
for i in range(N_fwh):
    denom = h_vapor[i] - h_liq_entradas[i]
    y = flujo_masa * (h_liq_salidas[i] - h_liq_entradas[i]) / denom if denom != 0 else 0
    y_frac.append(y)
    flujo_masa -= y
    flujos_bomba.append(flujo_masa)

# Balances Globales
w_turb_total = 1.0 * (h_in - h_vapor[0]) if N_fwh > 0 else 1.0 * (h_in - h_out_real)
if N_fwh > 0:
    flujo_t = 1.0
    for i in range(N_fwh - 1):
        flujo_t -= y_frac[i]
        w_turb_total += flujo_t * (h_vapor[i] - h_vapor[i+1])
    flujo_t -= y_frac[-1]
    w_turb_total += flujo_t * (h_vapor[-1] - h_out_real)

w_bombas_total = sum(f * w for f, w in zip(flujos_bomba, w_bombas_esp))
q_in = h_in - h_in_caldera
w_neto = w_turb_total - w_bombas_total
eta_th = w_neto / q_in if q_in != 0 else 0

# --- RESULTADOS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Eficiencia Térmica", f"{eta_th*100:.2f} %")
col2.metric("Trabajo Neto", f"{w_neto/1e3:.2f} kJ/kg")
col3.metric("Calor Suministrado (Qin)", f"{q_in/1e3:.2f} kJ/kg")
col4.metric("Flujo Condensador", f"{flujo_masa*100:.2f} %")

# --- GRÁFICA T-s ---
st.subheader("Diagrama Temperatura - Entropía (T-s)")

T_crit = CP.PropsSI('Tcrit', fluido)
T_rango = np.linspace(274.15, T_crit - 1.0, 200)
S_liq = [CP.PropsSI('S', 'T', T, 'Q', 0, fluido)/1e3 for T in T_rango]
S_vap = [CP.PropsSI('S', 'T', T, 'Q', 1, fluido)/1e3 for T in T_rango]

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(S_liq, T_rango - 273.15, 'k-', label='Campana Líquido')
ax.plot(S_vap, T_rango - 273.15, 'k-', label='Campana Vapor')

S_p = [CP.PropsSI('S', 'P', P_cond, 'Q', 0, fluido)/1e3]
T_p = [CP.PropsSI('T', 'P', P_cond, 'Q', 0, fluido) - 273.15]
S_p.extend([CP.PropsSI('S', 'P', P_cald, 'H', h_in_caldera, fluido)/1e3, s_in/1e3, s_out_real/1e3, S_p[0]])
T_p.extend([CP.PropsSI('T', 'P', P_cald, 'H', h_in_caldera, fluido) - 273.15, T_max_C, T_out, T_p[0]])

ax.plot(S_p, T_p, 'r-o', linewidth=2, label='Ciclo')
ax.set_xlabel('Entropía [kJ/kg·K]')
ax.set_ylabel('Temperatura [°C]')
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend()

st.pyplot(fig)
