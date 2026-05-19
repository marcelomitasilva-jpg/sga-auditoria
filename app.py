import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="SGA Pro v42.0 - Automatizado", layout="wide")

# LÓGICA DE LA LLAVE MAESTRA (SECRETS)
# El programa busca la clave en la "caja fuerte" de Streamlit Cloud
if "gemini_key" in st.secrets:
    api_key = st.secrets["gemini_key"]
    st.session_state.api_key = api_key
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    # No mostramos mensaje de error si la llave ya existe
elif 'api_key' in st.session_state and st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    with st.sidebar:
        st.warning("🔑 Llave no detectada. Ingrésala manualmente:")
        manual_key = st.text_input("Gemini API KEY", type="password")
        if manual_key:
            st.session_state.api_key = manual_key
            st.rerun()

# --- 2. MOTOR DE BASE DE DATOS ---
def conectar():
    return sqlite3.connect('sga_cooperativa.db')

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio_id INTEGER, monto REAL, fecha TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, descripcion TEXT, valor REAL)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN ---
st.sidebar.title("🛡️ CONTROL SGA")
if "gemini_key" in st.secrets:
    st.sidebar.success("✅ IA Conectada Automáticamente")

menu = st.sidebar.radio("MENÚ:", [
    "📊 1. Dashboard General",
    "👥 2. Registro de Personal",
    "⛏️ 3. Escáner IA (Auditoría)",
    "💰 4. Control de Vales",
    "🚜 5. Inventario de Activos",
    "📖 6. Libro Diario Central"
])

# --- LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen de la Cooperativa")
    st.write("Bienvenido al sistema en la nube, Marcelo.")

elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Personal")
    with st.form("form_p"):
        nombre = st.text_input("Nombre Completo").upper()
        ci = st.text_input("CI / Documento")
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); c = conn.cursor()
                c.execute("INSERT INTO personal (nombre, ci) VALUES (?,?)", (nombre, ci))
                conn.commit(); conn.close()
                st.success("Socio registrado.")
            except: st.error("Error: CI duplicado.")
    df_p = pd.read_sql_query("SELECT * FROM personal", conectar())
    st.dataframe(df_p, use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner Inteligente")
    archivo = st.file_uploader("Subir foto", type=['png', 'jpg', 'jpeg'])
    if archivo:
        img = Image.open(archivo); st.image(img, width=450)
        if st.button("🚀 INICIAR ANÁLISIS"):
            with st.spinner("Analizando..."):
                img_byte_arr = io.BytesIO(); img.save(img_byte_arr, format='JPEG')
                prompt = "Analiza esta tabla de minería. Responde SOLO JSON con: fecha, tujo, mina, bs, obs."
                try:
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_byte_arr.getvalue()}])
                    json_str = re.search(r'\[.*\]', response.text, re.DOTALL).group()
                    st.session_state.df_temp = pd.read_json(io.StringIO(json_str))
                except: st.error("Error al leer la imagen.")

    if 'df_temp' in st.session_state:
        df_editado = st.data_editor(st.session_state.df_temp, use_container_width=True)
        if st.button("💾 GUARDAR EN LIBRO DIARIO"):
            conn = conectar(); df_editado.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
            st.success("Guardado.")
            del st.session_state.df_temp

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario")
    df_final = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df_final, use_container_width=True)
