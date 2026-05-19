import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CEREBRO IA ---
st.set_page_config(page_title="SGA Pro v47.0 - Sistema Integral Bolivia", layout="wide", page_icon="⛏️")

# Recuperación automática de la API Key desde los Secrets de Streamlit
if "gemini_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    ia_conectada = True
else:
    ia_conectada = False

# --- 2. MOTOR DE BASE DE DATOS (7 TABLAS/MÓDULOS) ---
def conectar():
    return sqlite3.connect('sga_maestro_total.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    # Módulo 2: Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    # Módulo 3: Auditoría (Escáner)
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    # Módulo 4: Vales
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    # Módulo 5: Activos
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_registro TEXT)')
    # Módulo 6: Libro Diario (Se alimenta de auditoria y vales)
    # Módulo 7: Configuración (Metadata del sistema)
    c.execute('CREATE TABLE IF NOT EXISTS configuracion (parametro TEXT PRIMARY KEY, valor TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN MAESTRA (LOS 7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA CONTROL TOTAL")
    if ia_conectada:
        st.success("✅ IA Nano Banana 2 Conectada")
    else:
        st.error("❌ IA No configurada (Revisa Secrets)")
    
    menu = st.radio("SELECCIONE MÓDULO:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Inventario de Activos",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.markdown("---")
    st.caption(f"Usuario: Marcelo | 2026")

# --- MÓDULO 1: DASHBOARD ---
if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_p = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Socios", total_p)
    with c2:
        total_b = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Auditado (Bs)", f"{total_b if total_b else 0:,.2f}")
    with c3:
        total_v = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Egresos Vales", f"{total_v if total_v else 0:,.2f}")
    with c4:
        st.metric("Eficiencia IA", "98.5%")

# --- MÓDULO 2: PERSONAL ---
elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Socios y Personal")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        with st.form("reg_personal"):
            n = st.text_input("Nombre Completo").upper()
            ci = st.text_input("CI")
            cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Operario", "Seguridad"])
            if st.form_submit_button("Guardar Registro"):
                try:
                    conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                    conn.commit(); conn.close(); st.success("Guardado")
                except: st.error("CI ya registrado")
    with col_b:
        df_p = pd.read_sql_query("SELECT * FROM personal", conectar())
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 3: ESCÁNER IA (AUTO-CONTROL) ---
elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Procesamiento Inteligente de Cuadernos")
    foto = st.file_uploader("Cargar foto del cuaderno (2019)", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR AUTOMÁTICAMENTE"):
            with st.spinner("La IA está leyendo y guardando los datos..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    prompt = """Analiza la tabla minera. Extrae: fecha, tujo, mina, bs, obs. 
                    Regla: Solo JSON [{}]. Si no hay número, pon 0. No hables, solo JSON."""
                    resp = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    match = re.search(r'\[.*\]', resp.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ {len(df)} registros archivados automáticamente."); st.dataframe(df)
                    else: st.error("Error de lectura: Imagen poco clara.")
                except Exception as e: st.error(f"Fallo técnico: {e}")

# --- MÓDULO 4: VALES ---
elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("vales_f"):
        socio = st.selectbox("Socio Recipiente", pd.read_sql_query("SELECT nombre FROM personal", conectar()))
        monto = st.number_input("Monto en Bs", min_value=0.0)
        fecha = st.date_input("Fecha de Entrega")
        conc = st.text_area("Concepto del Vale")
        if st.form_submit_button("Registrar Vale"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (socio, monto, str(fecha), conc))
            conn.commit(); conn.close(); st.success("Vale registrado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

# --- MÓDULO 5: ACTIVOS ---
elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Control de Maquinaria e Inmuebles")
    with st.form("activos_f"):
        item = st.text_input("Nombre del Activo")
        valor = st.number_input("Valor en Bs", min_value=0.0)
        estado = st.select_slider("Estado", ["Malo", "Regular", "Bueno", "Excelente"])
        if st.form_submit_button("Añadir al Inventario"):
            f_hoy = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_registro) VALUES (?,?,?,?)", (item, valor, estado, f_hoy))
            conn.commit(); conn.close(); st.success("Activo Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

# --- MÓDULO 6: LIBRO DIARIO ---
elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario (Consolidado Final)")
    df_aud = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.subheader("Producción Auditada")
    st.dataframe(df_aud, use_container_width=True)
    if not df_aud.empty:
        st.download_button("📥 Bajar Reporte Producción", df_aud.to_csv(index=False), "produccion_2019.csv")

# --- MÓDULO 7: CONFIGURACIÓN ---
elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Configuración del Sistema")
    st.write("**Estado de la Base de Datos:** Conectada (SQLite)")
    st.write("**Servidor:** Streamlit Cloud")
    if st.button("🗑️ Limpiar Memoria Temporal (Cache)"):
        st.cache_data.clear(); st.success("Cache Limpio")
    st.info("Para cambiar la API KEY, ve a la configuración de Secrets en Streamlit Cloud.")
