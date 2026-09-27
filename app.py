# =========================================================
    # 1. DIAGRAMA T-s PROFESIONAL TIPO TEXTBOOK (ÇENGEL)
    # =========================================================
    st.markdown('<div class="section-header">📈 Diagrama Temperatura - Entropía (T-s)</div>', unsafe_allow_html=True)
    
    # 1. Campana de saturación de alta fidelidad
    T_crit = CP.PropsSI('Tcrit', fluido)
    T_campana = np.linspace(273.16, T_crit - 0.15, 300)
    s_liq_camp = [CP.PropsSI('S', 'T', t, 'Q', 0, fluido)/1e3 for t in T_campana]
    s_vap_camp = [CP.PropsSI('S', 'T', t, 'Q', 1, fluido)/1e3 for t in T_campana]

    fig, ax = plt.subplots(figsize=(11, 6.8), dpi=140)
    
    # Dibujar la campana de saturación continua
    s_campana = s_liq_camp + s_vap_camp[::-1]
    t_campana = [t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]]
    ax.plot(s_campana, t_campana, color='#1e293b', linewidth=2.0, zorder=2)
    # Sombra sutil bajo la campana (zona bifásica)
    ax.fill_between(s_liq_camp + s_vap_camp[::-1], [t - 273.15 for t in T_campana] + [t - 273.15 for t in T_campana[::-1]], 
                    color='#f1f5f9', alpha=0.5, zorder=1)

    # Función para trazar una isóbara real completa y continua
    def trazar_curva_isobara(P_pa, color='#94a3b8', estilo='-', label_p=''):
        T_sat = CP.PropsSI('T', 'P', P_pa, 'Q', 0, fluido)
        s_f = CP.PropsSI('S', 'P', P_pa, 'Q', 0, fluido)/1e3
        s_g = CP.PropsSI('S', 'P', P_pa, 'Q', 1, fluido)/1e3
        
        # 1. Líquido subenfriado
        T_sub = np.linspace(274.15, T_sat - 0.1, 40)
        s_sub = [CP.PropsSI('S', 'P', P_pa, 'T', t, fluido)/1e3 for t in T_sub]
        t_sub = [t - 273.15 for t in T_sub]
        
        # 2. Mezcla (línea horizontal plana)
        s_mezcla = [s_f, s_g]
        t_mezcla = [T_sat - 273.15, T_sat - 273.15]
        
        # 3. Vapor sobrecalentado
        T_sup = np.linspace(T_sat + 0.1, min(650.0 + 273.15, T_max_K + 50.0), 60)
        s_sup = [CP.PropsSI('S', 'P', P_pa, 'T', t, fluido)/1e3 for t in T_sup]
        t_sup = [t - 273.15 for t in T_sup]
        
        # Unir curva
        s_iso = s_sub + s_mezcla + s_sup
        t_iso = t_sub + t_mezcla + t_sup
        ax.plot(s_iso, t_iso, color=color, linestyle=estilo, linewidth=1.1, alpha=0.7, zorder=2)
        
        if label_p:
            idx_txt = int(len(s_sup) * 0.4)
            ax.text(s_sup[idx_txt] - 0.25, t_sup[idx_txt] + 12, label_p, 
                    fontsize=8.5, color='#475569', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor='#e2e8f0', alpha=0.9))

    # Trazar presiones nominales
    trazar_curva_isobara(P_cond_Pa, '#94a3b8', ':', f"{P_cond:.0f} kPa")
    if tiene_recal:
        trazar_curva_isobara(P_recal_Pa, '#94a3b8', ':', f"{P_recal/1e3:.1f} MPa")
    for f in fwh_configuracion:
        trazar_curva_isobara(f['presion']*1e3, '#cbd5e1', ':', f"{f['presion']/1e3:.2f} MPa" if f['presion']>=1000 else f"{f['presion']:.1f} kPa")
    trazar_curva_isobara(P_cald_Pa, '#64748b', '--', f"{P_cald/1e3:.1f} MPa")

    # Trazado de los procesos del ciclo
    if tiene_recal and num_fwh >= 2:
        # Estados exactos del ejemplo 10-6
        p_fwh_abierto = min(f['presion'] for f in fwh_configuracion) * 1e3
        
        # Estados clave (s, T)
        s_9 = s_in_turb/1e3
        t_9 = T_max
        
        s_10 = s_in_turb/1e3
        h_10_iso = CP.PropsSI('H', 'P', P_recal_Pa, 'S', s_in_turb, fluido)
        t_10 = get_T_safe(P_recal_Pa, h_10_iso)
        
        s_11 = s_rec_in2/1e3
        t_11 = T_recal
        
        s_12 = s_rec_in2/1e3
        h_12_iso = CP.PropsSI('H', 'P', p_fwh_abierto, 'S', s_rec_in2, fluido)
        t_12 = get_T_safe(p_fwh_abierto, h_12_iso)
        
        s_13 = s_out_turb/1e3
        t_13 = T_out_turb
        
        s_1 = s1/1e3
        t_1 = T1
        
        s_2 = s1/1e3
        t_2 = T1 + 3.0
        
        s_3 = CP.PropsSI('S', 'P', p_fwh_abierto, 'Q', 0, fluido)/1e3
        t_3 = CP.PropsSI('T', 'P', p_fwh_abierto, 'Q', 0, fluido) - 273.15
        
        s_4 = s_3
        t_4 = t_3 + 8.0
        
        s_6 = CP.PropsSI('S', 'P', P_recal_Pa, 'Q', 0, fluido)/1e3
        t_6 = CP.PropsSI('T', 'P', P_recal_Pa, 'Q', 0, fluido) - 273.15
        
        s_7 = s_6
        t_7 = t_6 + 10.0
        
        s_5 = s_6 - 0.22
        t_5 = t_6 - 7.0
        
        s_8 = s_6 - 0.08
        t_8 = t_6 + 4.0

        # Curva de caldera (4 -> 5 -> 8 -> 7 -> 9)
        T_caldera_curva = np.linspace(t_7 + 273.15, T_max_K, 30)
        s_caldera_curva = [CP.PropsSI('S', 'P', P_cald_Pa, 'T', t, fluido)/1e3 for t in T_caldera_curva]
        t_caldera_curva = [t - 273.15 for t in T_caldera_curva]
        
        # Curva de recalentador (10 -> 11)
        T_recal_curva = np.linspace(t_10 + 273.15, T_recal_K, 25)
        s_recal_curva = [CP.PropsSI('S', 'P', P_recal_Pa, 'T', t, fluido)/1e3 for t in T_recal_curva]
        t_recal_curva = [t - 273.15 for t in T_recal_curva]

        # 1. Expansiones en turbina (isentrópicas verticales)
        ax.plot([s_9, s_10], [t_9, t_10], color='#2563eb', linewidth=2.5, zorder=4)
        ax.plot([s_11, s_12, s_13], [t_11, t_12, t_13], color='#2563eb', linewidth=2.5, zorder=4)
        
        # 2. Recalentamiento en caldera
        ax.plot(s_recal_curva, t_recal_curva, color='#dc2626', linewidth=2.5, zorder=4)
        
        # 3. Condensación
        ax.plot([s_13, s_1], [t_13, t_1], color='#0284c7', linewidth=2.5, zorder=4)
        
        # 4. Bombeos y línea de alimentación líquida
        ax.plot([s_1, s_2, s_3, s_4, s_5, s_8, s_7], [t_1, t_2, t_3, t_4, t_5, t_8, t_7], color='#16a34a', linewidth=2.2, zorder=4)
        ax.plot(s_caldera_curva, t_caldera_curva, color='#16a34a', linewidth=2.5, zorder=4)
        
        # 5. Extracciones a calentadores
        ax.plot([s_10, s_6], [t_10, t_6], color='#7c3aed', linewidth=1.8, linestyle='-', zorder=3)
        ax.plot([s_6, s_7], [t_6, t_7], color='#16a34a', linewidth=1.8, zorder=3)
        ax.plot([s_12, s_3], [t_12, t_3], color='#7c3aed', linewidth=1.8, linestyle='-', zorder=3)

        # Puntos y Etiquetas con offsets optimizados para que NO se encimen
        puntos = [
            ((s_1, t_1), "1", (-14, -7)),
            ((s_2, t_2), "2", (-14, 2)),
            ((s_3, t_3), "3", (-14, -5)),
            ((s_4, t_4), "4", (-14, 4)),
            ((s_5, t_5), "5", (-15, 6)),
            ((s_6, t_6), "6", (6, -9)),
            ((s_7, t_7), "7", (6, 5)),
            ((s_8, t_8), "8", (-13, 10)),
            ((s_9, t_9), "9", (-14, 5)),
            ((s_10, t_10), "10", (8, -2)),
            ((s_11, t_11), "11", (7, 5)),
            ((s_12, t_12), "12", (8, 0)),
            ((s_13, t_13), "13", (8, -2))
        ]
        
        for coord, txt, offset in puntos:
            ax.plot(coord[0], coord[1], 'ko', markersize=4.2, zorder=5)
            ax.annotate(txt, xy=coord, xytext=offset, textcoords='offset points', 
                        fontsize=9.5, fontweight='bold', color='#0f172a', zorder=6)

        # Rótulos de flujos fraccionales estilizados
        ax.text(s_9 - 0.45, (t_9 + t_10)/2 + 25, '1 kg', fontsize=9.5, color='#1e293b', fontstyle='italic', fontweight='600')
        ax.text(s_11 + 0.15, (t_11 + t_12)/2 + 70, '1 - y', fontsize=9.5, color='#1e293b', fontstyle='italic', fontweight='600')
        ax.text((s_10 + s_6)/2, t_6 + 18, 'y', fontsize=9.5, color='#6d28d9', fontweight='bold')
        ax.text((s_12 + s_3)/2 + 0.5, t_3 + 18, 'z', fontsize=9.5, color='#6d28d9', fontweight='bold')
        ax.text(s_13 + 0.12, (t_12 + t_13)/2 - 35, '1 - y - z', fontsize=9.5, color='#1e293b', fontstyle='italic', fontweight='600')

    else:
        # Modo simple o recalentamiento estándar
        if tiene_recal:
            pts_s = [s1/1e3, s2/1e3, s_in_turb/1e3, s_rec_sal/1e3, s_rec_in2/1e3, s_out_turb/1e3, s1/1e3]
            pts_t = [T1, T2, T_max, T_rec_sal, T_recal, T_out_turb, T1]
            labels = ["1", "2", "3", "4", "5", "6"]
        else:
            pts_s = [s1/1e3, s2/1e3, s_in_turb/1e3, s_out_turb/1e3, s1/1e3]
            pts_t = [T1, T2, T_max, T_out_turb, T1]
            labels = ["1", "2", "3", "4"]

        ax.plot(pts_s, pts_t, color='#2563eb', marker='o', markersize=5, linewidth=2.2, zorder=4)
        for i, lbl in enumerate(labels):
            ax.annotate(lbl, xy=(pts_s[i], pts_t[i]), xytext=(7, 7), textcoords='offset points', 
                        fontsize=10, fontweight='bold', color='#0f172a')

    # Ajustes finales del lienzo
    ax.set_xlabel("Entropía, s [kJ/kg · K]", fontsize=10.5, fontweight='600', color='#1e293b')
    ax.set_ylabel("Temperatura, T [°C]", fontsize=10.5, fontweight='600', color='#1e293b')
    ax.set_xlim(-0.1, 9.2)
    ax.set_ylim(-20, max(680.0, T_max + 60.0))
    
    ax.grid(True, linestyle=':', alpha=0.45, color='#94a3b8')
    for sp in ['top', 'right']:
        ax.spines[sp].set_visible(False)
    for sp in ['left', 'bottom']:
        ax.spines[sp].set_color('#334155')
        ax.spines[sp].set_linewidth(1.3)
    ax.spines['left'].set_position(('outward', 8))
    ax.spines['bottom'].set_position(('outward', 8))

    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#ffffff')
    st.pyplot(fig)
