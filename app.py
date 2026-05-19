import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CEREBRO IA ---
st.set_page_config(page_title="SGA Pro v49.0 - Marcelo", layout="wide", page_icon="⛏️")

# CORRECCIÓN DE ERROR 404: Usamos el nombre de modelo compatible
if "gemini_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_key"])
    # Cambiamos a 'gemini-1.5-flash-latest' para máxima compatibilidad
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    ia_conectada = True
else:
    ia_conectada = False

# --- 2. BASE DE DATOS (7 MÓDULOS) ---
def conectar():
    return sqlite3.connect('sga_consolidado.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, evento TEXT, fecha TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN (LOS 7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA CONTROL TOTAL")
    if ia_conectada:
        st.success("✅ IA Nano Banana 2 Conectada")
    else:
        st.error("❌ Revisa los Secrets en Streamlit")
    
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
    st.caption("Usuario: Marcelo | 2026")

# --- MÓDULO 1: DASHBOARD ---
if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen Operativo")
    c1, c2, c3 = st.columns(3)
    with c1:
        total_p = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Socios", total_p)
    with c2:
        total_b = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Producción (Bs)", f"{total_b if total_b else 0:,.2f}")
    with c3:
        total_v = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Vales (Bs)", f"{total_v if total_v else 0:,.2f}")

# --- MÓDULO 2: PERSONAL ---
elif menu == "👥 2. Registro de Personal":
    st.title("👥 Gestión de Socios")
    with st.form("reg_p"):
        n = st.text_input("Nombre Completo").upper()
        ci = st.text_input("CI")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Operario"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                conn.commit(); conn.close(); st.success("Registrado")
            except: st.error("El CI ya existe")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

# --- MÓDULO 3: ESCÁNER IA ---
elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Procesamiento de Cuadernos")
    foto = st.file_uploader("Cargar imagen", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 PROCESAR Y ARCHIVAR AUTOMÁTICAMENTE"):
            with st.spinner("La IA está trabajando..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    prompt = "Extrae tabla JSON: [fecha, tujo, mina, bs, obs]. Solo JSON. Si vacío, 0."
                    resp = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    match = re.search(r'\[.*\]', resp.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ {len(df)} registros archivados."); st.dataframe(df)
                    else: st.error("No se detectó tabla. Intenta una foto más clara.")
                except Exception as e: st.error(f"Error: {e}")

# --- MÓDULO 4: VALES ---
elif menu == "💰 4. Vales y Adelantos":
    st.title("💰 Control de Vales")
    with st.form("v_f"):
        s = st.selectbox("Socio", pd.read_sql_query("SELECT nombre FROM personal", conectar()))
        m = st.number_input("Monto (Bs)", min_value=0.0)
        f = st.date_input("Fecha")
        c = st.text_input("Concepto")
        if st.form_submit_button("Guardar Vale"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (s, m, str(f), c))
            conn.commit(); conn.close(); st.success("Vale guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM vales", conectar()), use_container_width=True)

# --- MÓDULO 5: ACTIVOS ---
elif menu == "🚜 5. Inventario de Activos":
    st.title("🚜 Maquinaria e Inmuebles")
    with st.form("a_f"):
        i = st.text_input("Activo")
        v = st.number_input("Valor (Bs)", min_value=0.0)
        e = st.selectbox("Estado", ["Bueno", "Regular", "Reparación"])
        if st.form_submit_button("Registrar"):
            f = datetime.now().strftime("%Y-%m-%d")
            conn = conectar(); conn.execute("INSERT INTO activos (item, valor, estado, fecha_reg) VALUES (?,?,?,?)", (i, v, e, f))
            conn.commit(); conn.close(); st.success("Activo Guardado")
    st.dataframe(pd.read_sql_query("SELECT * FROM activos", conectar()), use_container_width=True)

# --- MÓDULO 6: LIBRO DIARIO ---
elif menu == "📖 6. Libro Diario Central":
    st.title("📖 Libro Diario")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.download_button("📥 Descargar CSV", df.to_csv(index=False), "auditoria.csv")

# --- MÓDULO 7: CONFIGURACIÓN ---
elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Sistema")
    st.write("Base de Datos SQLite activa.")
    if st.button("🗑️ Limpiar Cache"):
        st.cache_data.clear(); st.success("Cache Limpio")
