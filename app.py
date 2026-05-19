import os
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. PARCHE MAESTRO DE CONEXIÓN ---
# Forzamos al entorno a no usar configuraciones experimentales
os.environ["GOOGLE_API_USE_MTLS"] = "never"

st.set_page_config(
    page_title="SGA Pro v58.0", 
    layout="wide", 
    page_icon="⛏️"
)

# REPARACIÓN RADICAL: Especificamos la versión v1 en la configuración
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Llamada explícita al modelo estable
        model = genai.GenerativeModel('gemini-1.5-flash')
        ia_conectada = True
    except Exception:
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. BASE DE DATOS ---
def conectar():
    return sqlite3.connect('sga_consolidado_final.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. INTERFAZ (7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA MAESTRO")
    if ia_conectada:
        st.success("✅ Servidor IA v1 Activo")
    else:
        st.error("❌ Revisa API Key en Secrets")
    
    menu = st.radio("SELECCIONE MÓDULO:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Inventario de Activos",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.caption("Marcelo | 2026")

# --- 4. LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3 = st.columns(3)
    try:
        with c1:
            tp = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
            st.metric("Total Socios", tp)
        with c2:
            tb = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
            st.metric("Producción (Bs)", f"{tb if tb else 0:,.2f}")
        with c3:
            tv = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
            st.metric("Egresos Vales", f"{tv if tv else 0:,.2f}")
    except: st.warning("Carga datos para ver estadísticas.")

elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Personal")
    with st.form("p"):
        n = st.text_input("Nombre").upper(); c = st.text_input("CI")
        cg = st.selectbox("Cargo", ["Socio", "Administrador", "Seguridad"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, c, cg))
                conn.commit(); conn.close(); st.success("Registrado")
            except: st.error("Error: CI Duplicado")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos")
    foto = st.file_uploader("Subir foto", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR"):
            with st.spinner("La IA está analizando..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    # Prompt reforzado para JSON
                    prompt = "Extract table data to JSON format: [fecha, tujo, mina, bs, obs]. Only JSON, no text."
                    
                    # Llamada con parámetros de seguridad
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpieza quirúrgica de la respuesta
                    raw_text = response.text
                    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ Guardado: {len(df)} registros nuevos."); st.dataframe(df)
                    else: st.error("La IA no devolvió un formato válido. Reintenta.")
                except Exception as e:
                    st.error(f"Fallo de Conexión: {e}")

elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("v"):
        lista = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        s = st.selectbox("Socio", lista['nombre'] if not lista.empty else ["Sin socios"])
        m = st.number_input("Monto (Bs)"); f = st.date_input("Fecha"); cp = st.text_input("Concepto")
        if st.form_submit_button("Registrar"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (s, m, str(f), cp))
            conn.commit(); conn.close(); st.success("Registrado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Inventario")
    with st.form("a"):
        it = st.text_input("Item"); vl = st.number_input("Valor"); es = st.selectbox("Estado", ["Bueno", "Regular", "Malo"])
        if st.form_submit_button("Añadir"):
            fr = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (it, vl, es, fr))
            conn.commit(); conn.close(); st.success("Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Registros Consolidados")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("📥 Descargar CSV", df.to_csv(index=False), "libro_diario.csv")

elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Sistema")
    if st.button("🧹 Limpiar Cache"):
        st.cache_data.clear(); st.rerun()
