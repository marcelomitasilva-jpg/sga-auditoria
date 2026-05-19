import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y SOLUCIÓN DE CONEXIÓN ---
st.set_page_config(page_title="SGA Pro v51.0 - Control Maestro", layout="wide", page_icon="⛏️")

# CLAVE DEL ÉXITO: Forzamos la conexión a la API estable v1
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Usamos el nombre de modelo base sin sufijos que causan el 404
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        ia_conectada = True
    except Exception as e:
        st.error(f"Error de configuración: {e}")
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. BASE DE DATOS (7 MÓDULOS) ---
def conectar():
    return sqlite3.connect('sga_final_marcelo.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN (INTEGRACIÓN TOTAL) ---
with st.sidebar:
    st.title("🛡️ SGA BOLIVIA")
    if ia_conectada:
        st.success("✅ Conexión Estable con Gemini")
    else:
        st.error("❌ Revisa API Key en Secrets")
    
    menu = st.radio("SELECCIONE MÓDULO:", [
        "📊 1. Dashboard General",
        "👥 2. Personal y Socios",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Activos e Inventario",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.markdown("---")
    st.caption("Marcelo | Cooperativa 2026")

# --- LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen de Operaciones")
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
    st.title("👥 Registro de Personal")
    with st.form("p_form"):
        n = st.text_input("Nombre Completo").upper(); ci = st.text_input("CI")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Seguridad"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                conn.commit(); conn.close(); st.success("Guardado con éxito")
            except: st.error("El CI ya existe")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos 2019")
    foto = st.file_uploader("Cargar foto", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 ANALIZAR Y GUARDAR AUTOMÁTICAMENTE"):
            with st.spinner("Procesando imagen..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    # Prompt técnico simplificado para evitar errores de red
                    prompt = "Analiza la tabla. Extrae JSON: [fecha, tujo, mina, bs, obs]. Solo JSON puro, sin texto extra."
                    
                    # Llamada corregida
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpiador de seguridad
                    raw_text = response.text
                    match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar()
                        df.to_sql('auditoria', conn, if_exists='append', index=False)
                        conn.close()
                        st.success(f"✅ ¡Éxito! {len(df)} registros archivados.")
                        st.dataframe(df)
                    else:
                        st.error("No se pudo estructurar la información. Intenta otra foto.")
                except Exception as e:
                    st.error(f"Error de sistema: {e}")

elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("v_form"):
        lista = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        socio = st.selectbox("Socio", lista['nombre'] if not lista.empty else ["Sin socios"])
        monto = st.number_input("Monto en Bs", min_value=0.0)
        f = st.date_input("Fecha")
        c = st.text_input("Concepto")
        if st.form_submit_button("Registrar Vale"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (socio, monto, str(f), c))
            conn.commit(); conn.close(); st.success("Vale registrado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

elif menu == "🚜 5. Activos e Inventario":
    st.title("🚜 Inventario de Maquinaria")
    with st.form("a_form"):
        item = st.text_input("Activo"); valor = st.number_input("Valor (Bs)"); est = st.selectbox("Estado", ["Bueno", "Regular", "Reparación"])
        if st.form_submit_button("Añadir"):
            f_hoy = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (item, valor, est, f_hoy))
            conn.commit(); conn.close(); st.success("Activo Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario (Consolidado)")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("📥 Descargar Excel", df.to_csv(index=False), "auditoria.csv")

elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Estado del Sistema")
    st.info("Versión 51.0 | Base de Datos: sga_final_marcelo.db")
    if st.button("🗑️ Limpiar Cache de Navegador"):
        st.cache_data.clear(); st.rerun()
