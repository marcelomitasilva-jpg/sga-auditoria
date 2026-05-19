import os
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y PARCHE DE RED RADICAL ---
# Esto obliga a la librería a usar la conexión estándar v1
os.environ["GOOGLE_API_USE_MTLS"] = "never"

st.set_page_config(
    page_title="SGA Pro v57.0 - Marcelo", 
    layout="wide", 
    page_icon="⛏️"
)

# REPARACIÓN DE CONEXIÓN: Usamos el método de inicialización más simple posible
if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # Eliminamos 'models/' del nombre para que la API elija la ruta v1 automáticamente
        model = genai.GenerativeModel('gemini-1.5-flash')
        ia_conectada = True
    except Exception:
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. MOTOR DE BASE DE DATOS ---
def conectar():
    return sqlite3.connect('sga_maestro_marcelo.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. MENÚ (7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA BOLIVIA")
    if ia_conectada:
        st.success("✅ Conexión Estable")
    else:
        st.error("❌ Error de API Key")
    
    menu = st.radio("MÓDULOS:", [
        "📊 1. Dashboard General",
        "👥 2. Registro de Personal",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Vales y Adelantos",
        "🚜 5. Inventario de Activos",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.caption("Marcelo | Cooperativa 2026")

# --- 4. LÓGICA DE MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3 = st.columns(3)
    with c1:
        tp = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Total Socios", tp)
    with c2:
        tb = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Producción (Bs)", f"{tb if tb else 0:,.2f}")
    with c3:
        tv = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Egresos Vales", f"{tv if tv else 0:,.2f}")

elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Personal")
    with st.form("p_form"):
        n = st.text_input("Nombre").upper(); c = st.text_input("CI")
        cg = st.selectbox("Cargo", ["Socio", "Administrador", "Seguridad"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, c, cg))
                conn.commit(); conn.close(); st.success("Guardado")
            except: st.error("Error: CI Duplicado")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos")
    foto = st.file_uploader("Subir foto", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR"):
            with st.spinner("IA trabajando..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    # Prompt simplificado para evitar errores de red
                    prompt = "Extract table data to JSON: [fecha, tujo, mina, bs, obs]. Only JSON."
                    
                    # Llamada directa al modelo
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpiador de texto extra
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ {len(df)} filas guardadas."); st.dataframe(df)
                    else: st.error("No se detectó tabla.")
                except Exception as e:
                    st.error(f"Error técnico: {e}")

elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("v_form"):
        lista = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        s = st.selectbox("Socio", lista['nombre'] if not lista.empty else ["Sin socios"])
        m = st.number_input("Monto (Bs)"); f = st.date_input("Fecha"); cp = st.text_input("Concepto")
        if st.form_submit_button("Registrar"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (s, m, str(f), cp))
            conn.commit(); conn.close(); st.success("Registrado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Inventario")
    with st.form("a_form"):
        it = st.text_input("Item"); vl = st.number_input("Valor"); es = st.selectbox("Estado", ["Bueno", "Malo"])
        if st.form_submit_button("Añadir"):
            fr = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (it, vl, es, fr))
            conn.commit(); conn.close(); st.success("Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)

elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Sistema")
    if st.button("🧹 Limpiar Cache"):
        st.cache_data.clear(); st.rerun()
