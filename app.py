import streamlit as st
import google.generativeai as genai
import sqlite3
import pandas as pd
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SGA Pro v67.0", layout="wide", page_icon="🛡️")

# --- 2. CONEXIÓN A LA IA (CORREGIDA PARA FORZAR V1) ---
ia_conectada = False
if "gemini_key" in st.secrets:
    try:
        # El truco definitivo: Forzamos la API v1 mediante las opciones del cliente
        from google.api_core import client_options
        opciones = client_options.ClientOptions(api_version="v1")
        
        genai.configure(api_key=st.secrets["gemini_key"], client_options=opciones)
        model = genai.GenerativeModel('gemini-1.5-flash')
        ia_conectada = True
    except Exception as e:
        st.sidebar.error(f"Error de Configuración IA: {e}")

# --- 3. MOTOR DE BASE DE DATOS LOCAL ---
def conectar():
    return sqlite3.connect('sga_sistema_v67.db', check_same_thread=False)

def inicializar_db():
    conn = conectar()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS auditoria 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS personal 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vales 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)''')
    conn.commit()
    conn.close()

inicializar_db()

# --- 4. MENÚ LATERAL DE CONTROL ---
with st.sidebar:
    st.title("🛡️ SGA BOLIVIA")
    if ia_conectada:
        st.success("✅ IA Conectada (v1 Estable)")
    else:
        st.error("❌ IA Desconectada (Revisa Secrets)")
    
    menu = st.radio("MÓDULOS DEL SISTEMA:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "📖 5. Libro Diario Central"
    ])
    st.markdown("---")
    st.caption("Usuario: Marcelo | Gestión 2026")

# --- 5. DESARROLLO DE LOS MÓDULOS DEL SISTEMA ---

# --- MÓDULO 1: DASHBOARD GENERAL ---
if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    st.markdown("Estadísticas en tiempo real de la cooperativa.")
    
    try:
        conn = conectar()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_socios = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conn).iloc[0]['t']
            st.metric("Socios Registrados", f"{total_socios} Personas")
        
        with col2:
            total_bs = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conn).iloc[0]['t']
            st.metric("Producción Auditada (Bs)", f"{total_bs or 0:,.2f} Bs")
            
        with col3:
            total_vales = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conn).iloc[0]['t']
            st.metric("Total Vales Emitidos", f"{total_vales or 0:,.2f} Bs")
            
        conn.close()
    except Exception:
        st.info("Inicia el registro de datos para calcular métricas generales.")

# --- MÓDULO 2: REGISTRO DE PERSONAL ---
elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Socios y Personal")
    
    with st.form("form_personal"):
        nombre = st.text_input("Nombre Completo").upper()
        ci = st.text_input("Cédula de Identidad (CI)")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Contador", "Seguridad", "Operario"])
        
        if st.form_submit_button("Guardar Socio"):
            if nombre and ci:
                try:
                    conn = conectar()
                    conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (nombre, ci, cargo))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {nombre} ha sido guardado exitosamente.")
                except Exception:
                    st.error("Error: Este número de CI ya se encuentra registrado.")
            else:
                st.warning("Por favor, rellene los campos obligatorios.")
    
    st.markdown("---")
    st.subheader("📋 Personal Registrado en el Sistema")
    df_p = pd.read_sql_query("SELECT nombre as 'Nombre Completo', ci as 'Cédula de Identidad', cargo as 'Cargo' FROM personal", conectar())
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("No hay personal registrado todavía.")

# --- MÓDULO 3: ESCÁNER IA (AUDITORÍA) ---
elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos con IA")
    st.info("Sube la foto del cuaderno de control para extraer los datos de producción automáticamente.")
    
    archivo = st.file_uploader("Seleccionar imagen del cuaderno...", type=['png', 'jpg', 'jpeg'])
    
    if archivo:
        img = Image.open(archivo)
        st.image(img, caption="Vista previa del cuaderno subido", width=500)
        
        if st.button("🚀 PROCESAR Y ARCHIVAR EN LIBRO DIARIO"):
            if not ia_conectada:
                st.error("La conexión con la IA falló. Revisa tus variables en Secrets.")
            else:
                with st.spinner("Leyendo manuscrito y procesando datos con Gemini..."):
                    try:
                        img_byte_arr = io.BytesIO()
                        img.save(img_byte_arr, format='JPEG')
                        
                        instruccion = (
                            "Extract the data table from the image. Return ONLY a valid JSON list of objects "
                            "with keys: fecha, tujo, mina, bs, obs. Do not write text before or after the JSON. "
                            "If any field is missing or unreadable, put null for text or 0 for numbers."
                        )
                        
                        # Llamada limpia y estándar (la versión v1 ya fue configurada de raíz arriba)
                        response = model.generate_content(
                            contents=[instruccion, {'mime_type': 'image/jpeg', 'data': img_byte_arr.getvalue()}]
                        )
                        
                        texto_limpio = re.search(r'\[.*\]', response.text, re.DOTALL).group()
                        datos_df = pd.read_json(io.StringIO(texto_limpio))
                        
                        conn = conectar()
                        datos_df.to_sql('auditoria', conn, if_exists='append', index=False)
                        conn.close()
                        
                        st.success(f"✅ ¡Éxito! Se han extraído y guardado {len(datos_df)} filas en el Libro Diario.")
                        st.dataframe(datos_df, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"Fallo técnico al analizar la imagen: {e}")

# --- MÓDULO 4: VALES Y ADELANTOS ---
elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales y Adelantos")
    
    with st.form("form_vales"):
        res_p = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        lista_socios = res_p['nombre'].tolist() if not res_p.empty else ["No hay socios registrados"]
        
        socio = st.selectbox("Seleccionar Beneficiario", lista_socios)
        monto = st.number_input("Monto Entregado (Bs)", min_value=0.0, step=10.0)
        fecha = st.date_input("Fecha del Desembolso")
        concepto = st.text_input("Concepto o Motivo (Ej: Adelanto quincenal)")
        
        if st.form_submit_button("Registrar Vale en el Historial"):
            if socio != "No hay socios registrados":
                try:
                    conn = conectar()
                    conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", 
                                 (socio, monto, str(fecha), concepto))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ Vale de {monto} Bs asignado correctamente a {socio}.")
                except Exception as e:
                    st.error(f"Error al guardar el vale: {e}")
            else:
                st.error("Operación cancelada. Primero registre un socio en el Módulo 2.")

# --- MÓDULO 5: LIBRO DIARIO CENTRAL ---
elif menu == "📖 5. Libro Diario Central":
    st.title("📖 Libro Diario Centralizado")
    
    tab1, tab2 = st.tabs(["⛏️ Datos del Escáner (Auditoría)", "💰 Registro General de Vales"])
    
    with tab1:
        st.subheader("Registros Extraídos de Cuadernos")
        df_aud = pd.read_sql_query("SELECT id as 'ID', fecha as 'Fecha', tujo as 'Tujo', mina as 'Mina', bs as 'Monto (Bs)', obs as 'Observaciones' FROM auditoria", conectar())
        if not df_aud.empty:
            st.dataframe(df_aud, use_container_width=True)
            st.download_button("📥 Descargar Tabla de Auditoría (CSV)", df_aud.to_csv(index=False), "auditoria_cuadernos.csv", "text/csv")
        else:
            st.info("No hay datos procesados por el escáner IA en este momento.")
            
    with tab2:
        st.subheader("Historial de Vales Entregados")
        df_val = pd.read_sql_query("SELECT id as 'ID', socio as 'Socio Beneficiario', monto as 'Monto (Bs)', fecha as 'Fecha de Entrega', concepto as 'Concepto' FROM vales", conectar())
        if not df_val.empty:
            st.dataframe(df_val, use_container_width=True)
            st.download_button("📥 Descargar Historial de Vales (CSV)", df_val.to_csv(index=False), "registro_vales.csv", "text/csv")
        else:
            st.info("No se han registrado vales manuales en el sistema.")
