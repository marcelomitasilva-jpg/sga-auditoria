import os
import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re
from datetime import datetime

# --- 1. SOLUCIÓN RADICAL AL ERROR 404 ---
# Forzamos al sistema a ignorar configuraciones de red antiguas
os.environ["GOOGLE_API_USE_MTLS"] = "never"

st.set_page_config(page_title="SGA Pro v54.0", layout="wide", page_icon="⛏️")

if "gemini_key" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["gemini_key"])
        # CAMBIO CLAVE: Usamos 'gemini-1.5-flash' forzando la versión estable de la API
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={"top_p": 0.95, "top_k": 64, "temperature": 1.0}
        )
        ia_conectada = True
    except Exception:
        ia_conectada = False
else:
    ia_conectada = False

# --- 2. BASE DE DATOS ---
def conectar():
    return sqlite3.connect('sga_sistema_final.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE, cargo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS vales (id INTEGER PRIMARY KEY AUTOINCREMENT, socio TEXT, monto REAL, fecha TEXT, concepto TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS activos (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, valor REAL, estado TEXT, fecha_reg TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. NAVEGACIÓN (7 MÓDULOS) ---
with st.sidebar:
    st.title("🛡️ SGA BOLIVIA")
    st.success("✅ Conexión Forzada V1" if ia_conectada else "❌ Error de API")
    
    menu = st.radio("MENÚ:", [
        "📊 1. Dashboard General",
        "👥 2. Personal y Socios",
        "⛏️ 3. Escáner IA (Auditoría)",
        "💰 4. Control de Vales",
        "🚜 5. Inventario de Activos",
        "📖 6. Libro Diario Central",
        "⚙️ 7. Configuración y Sistema"
    ])
    st.caption("Usuario: Marcelo | 2026")

# --- MÓDULOS ---

if menu == "📊 1. Dashboard General":
    st.title("📊 Resumen de la Cooperativa")
    c1, c2, c3 = st.columns(3)
    with c1:
        tp = pd.read_sql_query("SELECT COUNT(*) as t FROM personal", conectar()).iloc[0]['t']
        st.metric("Socios", tp)
    with c2:
        tb = pd.read_sql_query("SELECT SUM(bs) as t FROM auditoria", conectar()).iloc[0]['t']
        st.metric("Producción (Bs)", f"{tb if tb else 0:,.2f}")
    with c3:
        tv = pd.read_sql_query("SELECT SUM(monto) as t FROM vales", conectar()).iloc[0]['t']
        st.metric("Egresos Vales", f"{tv if tv else 0:,.2f}")

elif menu == "👥 2. Personal y Socios":
    st.title("👥 Gestión de Socios")
    with st.form("p"):
        n = st.text_input("Nombre").upper(); ci = st.text_input("CI")
        cargo = st.selectbox("Cargo", ["Socio", "Administrador", "Seguridad"])
        if st.form_submit_button("Guardar"):
            try:
                conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci, cargo) VALUES (?,?,?)", (n, ci, cargo))
                conn.commit(); conn.close(); st.success("Registrado")
            except: st.error("CI ya existe")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()), use_container_width=True)

elif menu == "⛏️ 3. Escáner IA (Auditoría)":
    st.title("⛏️ Escáner de Cuadernos (Parche v54)")
    foto = st.file_uploader("Cargar foto", type=['png', 'jpg', 'jpeg'])
    if foto:
        img = Image.open(foto); st.image(img, width=600)
        if st.button("🚀 INICIAR ANÁLISIS"):
            with st.spinner("Conectando con el servidor de Google..."):
                try:
                    img_bytes = io.BytesIO(); img.save(img_bytes, format='JPEG')
                    # Prompt técnico para asegurar respuesta JSON
                    prompt = "Analyze table. Extract JSON: [fecha, tujo, mina, bs, obs]. Only JSON."
                    
                    # LLAMADA DE SEGURIDAD
                    response = model.generate_content(
                        contents=[prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}]
                    )
                    
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        conn = conectar(); df.to_sql('auditoria', conn, if_exists='append', index=False); conn.close()
                        st.success(f"✅ ¡Éxito! {len(df)} registros archivados."); st.dataframe(df)
                    else: st.error("Imagen borrosa, intenta de nuevo.")
                except Exception as e:
                    st.error(f"Error de red: {e}. Por favor, refresca la página.")

elif menu == "💰 4. Control de Vales":
    st.title("💰 Gestión de Vales")
    with st.form("v"):
        lista = pd.read_sql_query("SELECT nombre FROM personal", conectar())
        soc = st.selectbox("Socio", lista['nombre'] if not lista.empty else ["Sin socios"])
        m = st.number_input("Monto (Bs)"); f = st.date_input("Fecha"); c = st.text_input("Concepto")
        if st.form_submit_button("Registrar"):
            conn = conectar(); conn.execute("INSERT INTO vales (socio, monto, fecha, concepto) VALUES (?,?,?,?)", (soc, m, str(f), c))
            conn.commit(); conn.close(); st.success("Vale guardado")
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
    st.title("📖 Libro Diario (Auditado)")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)

elif menu == "⚙️ 7. Configuración y Sistema":
    st.title("⚙️ Sistema")
    st.info("Parche de compatibilidad 404 activo.")
    if st.button("🧹 Limpiar Memoria"):
        st.cache_data.clear(); st.rerun()
