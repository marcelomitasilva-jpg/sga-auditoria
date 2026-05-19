import os
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN DE CONEXIÓN FORZADA ---
st.set_page_config(page_title="SGA Pro v60.0", layout="wide", page_icon="⛏️")

# Forzamos al sistema a usar la API estable 'v1'
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Configuramos el modelo sin prefijos experimentales
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash'
        )
        ia_conectada = True
    except Exception:
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. BASE DE DATOS ---
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

# --- 3. MENÚ DE NAVEGACIÓN ---
with st.sidebar:
    st.title("🛡️ SGA CONTROL TOTAL")
    if ia_conectada:
        st.success("✅ Conexión V1 Activa")
    else:
        st.error("❌ Revisa API Key")
    
    menu = st.radio("SELECCIONE MÓDULO:", [
        "📊 1. Dashboard",
        "👥 2. Personal",
        "⛏️ 3. Escáner IA",
        "💰 4. Vales",
        "🚜 5. Activos",
        "📖 6. Libro Diario",
        "⚙️ 7. Sistema"
    ])
    st.caption("Marcelo | 2026")

# --- 4. LÓGICA DE MÓDULOS ---

if menu == "⛏️ 3. Escáner IA":
    st.title("⛏️ Escáner de Cuadernos")
    foto = st.file_uploader("Subir foto del cuaderno", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR"):
            with st.spinner("Conectando con Google V1..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    prompt = "Extrae los datos de la tabla. Formato JSON: [fecha, tujo, mina, bs, obs]. Solo JSON puro."
                    
                    # LLAMADA CON PARCHE DE SEGURIDAD (Forzamos la versión v1)
                    from google.generativeai.types import RequestOptions
                    response = model.generate_content(
                        contents=[prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}],
                        request_options=RequestOptions(api_version='v1')
                    )
                    
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ Éxito: {len(df)} registros guardados."); st.dataframe(df)
                    else: st.error("La IA no detectó la tabla. Intenta una foto más clara.")
                except Exception as e:
                    st.error(f"Fallo de conexión: {e}")

elif menu == "📊 1. Dashboard":
    st.title("📊 Resumen Operativo")
    try:
        conn = conectar()
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Socios", pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conn).iloc[0]['t'])
        with c2: st.metric("Producción (Bs)", f"{pd.read_sql_query('SELECT SUM(bs) as t FROM auditoria', conn).iloc[0]['t'] or 0:,.2f}")
        with c3: st.metric("Vales (Bs)", f"{pd.read_sql_query('SELECT SUM(monto) as t FROM vales', conn).iloc[0]['t'] or 0:,.2f}")
        conn.close()
    except: st.info("Sin datos.")

elif menu == "👥 2. Personal":
    st.title("👥 Personal")
    with st.form("p"):
        n = st.text_input("Nombre").upper(); ci = st.text_input("CI")
        cg = st.selectbox("Cargo", ["Socio", "Administrador"])
        if st.form_submit_button("Guardar"):
            conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cg))
            conn.commit(); conn.close(); st.success("Registrado")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()))

elif menu == "💰 4. Vales":
    st.title("💰 Vales")
    with st.form("v"):
        res = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        s = st.selectbox("Socio", res['nombre'] if not res.empty else ["Sin socios"])
        m = st.number_input("Monto"); f = st.date_input("Fecha"); c = st.text_input("Concepto")
        if st.form_submit_button("Registrar"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (s, m, str(f), c))
            conn.commit(); conn.close(); st.success("Vale guardado")

elif menu == "🚜 5. Activos":
    st.title("🚜 Activos")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()))

elif menu == "📖 6. Libro Diario":
    st.title("📖 Registros Consolidados")
    st.dataframe(pd.read_sql_query("SELECT * FROM auditoria", conectar()))

elif menu == "⚙️ 7. Sistema":
    st.title("⚙️ Configuración")
    if st.button("Limpiar Memoria"): st.cache_data.clear(); st.rerun()
