import streamlit as st
import google.generativeai as genai
import sqlite3
import pandas as pd
from PIL import Image
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SGA Pro v61.0", layout="wide")

# --- CONEXIÓN RADICAL (PARCHE 404) ---
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Forzamos la creación del modelo sin configuraciones adicionales
        model = genai.GenerativeModel('gemini-1.5-flash')
        ia_conectada = True
    except:
        ia_conectada = False
else:
    ia_conectada = False

# --- BASE DE DATOS ---
def conectar():
    return sqlite3.connect('sga_maestro_final.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- INTERFAZ ---
with st.sidebar:
    st.title("🛡️ SGA MAESTRO")
    st.success("✅ IA Lista") if ia_conectada else st.error("❌ Error API")
    menu = st.radio("MENÚ:", ["📊 Dashboard", "👥 Personal", "⛏️ Escáner IA", "💰 Vales", "🚜 Activos", "📖 Libro Diario"])

# --- LÓGICA DEL ESCÁNER ---
if menu == "⛏️ Escáner IA":
    st.title("⛏️ Escáner de Cuadernos")
    foto = st.file_uploader("Subir imagen", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 ANALIZAR Y GUARDAR"):
            with st.spinner("Procesando..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    prompt = "Analiza la tabla y devuelve JSON: [fecha, tujo, mina, bs, obs]. Solo JSON."
                    
                    # LLAMADA CON FORZADO DE VERSIÓN V1
                    from google.generativeai.types import RequestOptions
                    response = model.generate_content(
                        contents=[prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}],
                        request_options=RequestOptions(api_version='v1')
                    )
                    
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success("✅ Datos guardados."); st.dataframe(df)
                    else: st.error("Formato no detectado.")
                except Exception as e:
                    st.error(f"Error: {e}")

# --- RESTO DE MÓDULOS SIMPLIFICADOS ---
elif menu == "📊 Dashboard":
    st.title("📊 Resumen")
    conn = conectar()
    st.metric("Total Registros Auditoría", pd.read_sql_query("SELECT COUNT(*) FROM auditoria", conn).iloc[0,0])
    conn.close()

elif menu == "👥 Personal":
    st.title("👥 Personal")
    with st.form("p"):
        n = st.text_input("Nombre"); c = st.text_input("CI")
        if st.form_submit_button("Guardar"):
            conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci) VALUES (?,?)", (n, c)); conn.commit(); conn.close()
            st.success("Registrado")

elif menu == "📖 Libro Diario":
    st.title("📖 Registros")
    st.dataframe(pd.read_sql_query("SELECT * FROM auditoria", conectar()))
