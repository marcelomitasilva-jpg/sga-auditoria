import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y REPARACIÓN DE IA ---
st.set_page_config(page_title="SGA Pro v50.0", layout="wide", page_icon="⛏️")

if "gemini_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_key"])
    # SOLUCIÓN DEFINITIVA AL ERROR 404: Usamos el nombre base que es el más estable
    model = genai.GenerativeModel('gemini-1.5-flash')
    ia_conectada = True
else:
    ia_conectada = False

# --- 2. BASE DE DATOS MAESTRA ---
def conectar():
    return sqlite3.connect('sga_final.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN (LOS 7 MÓDULOS INTEGRALES) ---
with st.sidebar:
    st.title("🛡️ CONTROL TOTAL SGA")
    if ia_conectada:
        st.success("✅ IA Nano Banana 2 Activa")
    else:
        st.error("❌ Configura la API KEY en Secrets")
    
    menu = st.radio("MÓDULOS:", [
        "📊 1. Dashboard General",
        "👥 2. Personal y Socios",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Activos e Inventario",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.markdown("---")
    st.caption("Marcelo | Gestión 2026")

# --- LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3 = st.columns(3)
    with c1:
        tp = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Socios", tp)
    with c2:
        tb = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Producción (Bs)", f"{tb if tb else 0:,.2f}")
    with c3:
        tv = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Vales (Bs)", f"{tv if tv else 0:,.2f}")

elif menu == "👥 2. Personal y Socios":
    st.title("👥 Gestión de Personal")
    with st.form("p"):
        n = st.text_input("Nombre").upper(); ci = st.text_input("CI")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Seguridad"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                conn.commit(); conn.close(); st.success("Registrado")
            except: st.error("Error: CI duplicado")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner Automático (v50.0)")
    foto = st.file_uploader("Cargar foto", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR"):
            with st.spinner("La IA está leyendo los datos..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    # Prompt optimizado para evitar errores de red
                    prompt = "Analiza esta tabla. Extrae JSON: [fecha, tujo, mina, bs, obs]. Solo JSON puro."
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpiamos la respuesta de cualquier texto extra
                    cleaned_response = re.search(r'\[.*\]', response.text, re.DOTALL).group()
                    df = pd.read_json(io.StringIO(cleaned_response))
                    
                    conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                    st.success(f"✅ {len(df)} registros guardados automáticamente.")
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Fallo técnico: {e}. Intenta una foto más cercana.")

elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("v"):
        lista = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        soc = st.selectbox("Socio", lista['nombre'] if not lista.empty else ["Sin socios"])
        m = st.number_input("Monto (Bs)", min_value=0.0)
        f = st.date_input("Fecha")
        c = st.text_input("Concepto")
        if st.form_submit_button("Guardar Vale"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (soc, m, str(f), c))
            conn.commit(); conn.close(); st.success("Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

elif menu == "🚜 5. Activos e Inventario":
    st.title("🚜 Inventario")
    with st.form("a"):
        i = st.text_input("Item"); v = st.number_input("Valor (Bs)"); e = st.selectbox("Estado", ["Bueno", "Regular", "Reparación"])
        if st.form_submit_button("Registrar"):
            f = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (i, v, e, f))
            conn.commit(); conn.close(); st.success("Activo Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Registros Consolidados")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("📥 Descargar reporte", df.to_csv(index=False), "auditoria_sga.csv")

elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Estado del Sistema")
    st.info("Sistema operando en Streamlit Cloud con base de datos SQLite persistente.")
    if st.button("🧹 Limpiar Cache"):
        st.cache_data.clear(); st.rerun()
