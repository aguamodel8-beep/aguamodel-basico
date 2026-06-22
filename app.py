- Si falta algún valor, escribe `0` o deja la celda vacía.
- No uses puntos o comas para separar miles (ej. `580` en lugar de `580.0`).
- Si tu archivo tiene más columnas, la app las ignorará.
""")

# ------------------------------------------------------------
# 3.3 Selección de entrada
# ------------------------------------------------------------
opcion = st.radio("¿Cómo quieres ingresar los datos?", ("📁 Subir archivo", "✏️ Ingreso manual"))

if opcion == "📁 Subir archivo":
archivo = st.file_uploader("Selecciona un archivo (CSV o Excel)", type=["csv", "xlsx"])
if archivo is not None:
    try:
        if archivo.name.endswith('.csv'):
            # Detectar codificación del archivo CSV
            raw_data = archivo.read()
            encoding = chardet.detect(raw_data)['encoding']
            archivo.seek(0)
            df = pd.read_csv(archivo, encoding=encoding)
        else:
            df = pd.read_excel(archivo, engine='openpyxl')
        st.write("Vista previa de las primeras filas:")
        st.dataframe(df.head())
        columnas_requeridas = ['Ca', 'Mg', 'Na', 'K', 'HCO3', 'SO4', 'Cl', 'pH', 'Temp.(oC)']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if columnas_faltantes:
            st.error(f"❌ Faltan las siguientes columnas en tu archivo: {', '.join(columnas_faltantes)}. Por favor, asegúrate de que los nombres sean exactos.")
        else:
            st.subheader("Selecciona las unidades de tus datos")
            unidades_global = st.selectbox("Unidad común para todas las concentraciones", ["mg/L", "meq/L", "ppm"], key="unidades_global")
            if st.button("🔬 Procesar", key="procesar_archivo"):
                if st.session_state.muestras_procesadas >= 3:
                    st.error("⚠️ Has alcanzado el límite gratuito de 3 muestras. Para procesar más, contacta a Modelagua y adquiere el plan Profesional.")
                else:
                    num_muestras = len(df)
                    if st.session_state.muestras_procesadas + num_muestras > 3:
                        restantes = 3 - st.session_state.muestras_procesadas
                        st.warning(f"⚠️ Este archivo tiene {num_muestras} muestras. El plan gratuito solo permite {restantes} muestra(s) adicional(es). Por favor, sube un archivo con máximo {restantes} muestras o contacta para el plan de pago.")
                    else:
                        lista_informes = []
                        lista_resumen = []
                        for idx, row in df.iterrows():
                            datos_mg = {}
                            for param in ['Ca', 'Mg', 'Na', 'K', 'HCO3', 'SO4', 'Cl']:
                                val = row.get(param, 0)
                                if pd.isna(val) or val == '':
                                    val = 0
                                datos_mg[param] = convertir_a_mg_L(val, unidades_global, param)
                            temp = row.get('Temp.(oC)', 25.0)
                            if pd.isna(temp):
                                temp = 25.0
                            ph = row.get('pH', None)
                            if pd.isna(ph):
                                ph = None
                            nombre = f"Muestra_{idx+1}"
                            info = generar_informe(datos_mg, temp, ph, nombre)
                            lista_informes.append((nombre, info))
                            tds = sum(datos_mg.values())
                            meq,_,_,_,_ = balance_ionico(datos_mg)
                            tipo = kurlov(meq)
                            lista_resumen.append((nombre, tds, tipo))
                        st.session_state.muestras_procesadas += num_muestras
                        resumen = """
                        Balance iónico: Errores aceptables (<10%).
                        Clasificación Kurlov: Varía según muestra.
                        TDS: Rango salino o según cada muestra.
                        Relaciones iónicas: Exceso de sodio, mezcla calcita/dolomita, exceso HCO3.
                        Riesgo: Mayoría sobresaturada en calcita (incrustación), excepto si LI negativo (corrosión).
                        """
                        pdf = generar_pdf(lista_informes, resumen, lista_resumen)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            pdf.output(tmp.name)
                            with open(tmp.name, "rb") as f:
                                st.download_button("📥 Descargar informe PDF", f, file_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                            os.unlink(tmp.name)
                        st.success(f"✅ Procesamiento completado. Has usado {st.session_state.muestras_procesadas} de 3 muestras gratis.")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}. Asegúrate de que el formato sea correcto (CSV con coma como separador o Excel .xlsx).")

elif opcion == "✏️ Ingreso manual":
st.subheader("Ingresa los valores de una muestra (unidad: mg/L)")
cols = st.columns(2)
datos_manual = {}
with cols[0]:
    datos_manual['Ca'] = st.number_input("Ca (mg/L)", value=0.0, step=0.1, key="Ca_man")
    datos_manual['Mg'] = st.number_input("Mg (mg/L)", value=0.0, step=0.1, key="Mg_man")
    datos_manual['Na'] = st.number_input("Na (mg/L)", value=0.0, step=0.1, key="Na_man")
    datos_manual['K'] = st.number_input("K (mg/L)", value=0.0, step=0.1, key="K_man")
with cols[1]:
    datos_manual['HCO3'] = st.number_input("HCO3 (mg/L)", value=0.0, step=0.1, key="HCO3_man")
    datos_manual['SO4'] = st.number_input("SO4 (mg/L)", value=0.0, step=0.1, key="SO4_man")
    datos_manual['Cl'] = st.number_input("Cl (mg/L)", value=0.0, step=0.1, key="Cl_man")
    temp_man = st.number_input("Temperatura (°C)", value=25.0, step=0.1, key="temp_man")
    ph_man = st.number_input("pH", value=7.0, step=0.01, key="ph_man")
if st.button("🔬 Generar informe", key="procesar_manual"):
    if st.session_state.muestras_procesadas >= 3:
        st.error("⚠️ Límite gratuito alcanzado. Contacta para plan de pago.")
    else:
        datos_mg = {k: v for k, v in datos_manual.items()}
        if sum(datos_mg.values()) == 0:
            st.warning("⚠️ Todos los valores son cero. Ingresa al menos un parámetro.")
        else:
            info = generar_informe(datos_mg, temp_man, ph_man, "Muestra manual")
            st.text(info)
            lista_informes = [("Muestra manual", info)]
            tds = sum(datos_mg.values())
            meq,_,_,_,_ = balance_ionico(datos_mg)
            tipo = kurlov(meq)
            lista_resumen = [("Muestra manual", tds, tipo)]
            resumen = "Informe de una muestra manual."
            pdf = generar_pdf(lista_informes, resumen, lista_resumen)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf.output(tmp.name)
                with open(tmp.name, "rb") as f:
                    st.download_button("📥 Descargar PDF", f, file_name=f"informe_manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
                os.unlink(tmp.name)
            st.session_state.muestras_procesadas += 1
            st.success(f"✅ Procesado. Has usado {st.session_state.muestras_procesadas} de 3 muestras gratis.")

# ------------------------------------------------------------
# 3.6 Pie de página
# ------------------------------------------------------------
st.markdown("---")
st.caption("Modelagua - Análisis hidrogeoquímico básico. Para servicios profesionales, contacta con nosotros.")
