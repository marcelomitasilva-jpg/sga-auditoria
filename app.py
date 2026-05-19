import streamlit as st
import sqlite3
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
import re

# --- 1. CONFIGURACIÓN AUTOMÁTICA ---
st.set_page_config(page_title="SGA Pro v45.0 - Control Total", layout="wide")

# Conexión silenciosa con Nano Banana 2
if "gemini_key" in st.secrets:
    genai.configure(api_key=st.secrets["gemini_key"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("Falta la llave en Secrets. Ponla una vez y no la volverás a ver.")

# --- 2. BASE DE DATOS AUTOGESTIONADA ---
# El sistema se encarga de que nada se pierda
def conectar(): return sqlite3.connect('sga_sistema.db', check_same_thread=False)

def inicializar_db():
    conn = conectar(); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, ci TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, tujo REAL, mina REAL, bs REAL, obs TEXT)')
    conn.commit(); conn.close()

inicializar_db()

# --- 3. INTERFAZ LIMPIA (SIN CONFIGURACIONES) ---
st.sidebar.title("🛡️ SGA OPERACIONES")
menu = st.sidebar.radio("IR A:", ["📊 Resumen", "👥 Personal", "⛏️ ESCÁNER", "📖 REGISTROS"])

# --- 4. TOMA DE CONTROL: ESCÁNER IA ---
if menu == "⛏️ ESCÁNER":
    st.title("⛏️ Procesamiento Automático")
    st.write("Sube la foto. Yo me encargo del resto.")
    
    foto = st.file_uploader("Subir imagen del cuaderno", type=['png', 'jpg', 'jpeg'])
    
    if foto:
        img = Image.open(foto)
        st.image(img, width=500, caption="Documento detectado")
        
        # Procesamiento en un solo clic
        if st.button("🚀 PROCESAR Y GUARDAR AHORA"):
            with st.spinner("Analizando y archivando datos..."):
                try:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='JPEG')
                    
                    # Instrucción de control para la IA
                    prompt = "Extrae la tabla completa en JSON: [fecha, tujo, mina, bs, obs]. Pon 0 si está vacío."
                    response = model.generate_content([prompt, {'mime_type': 'image/jpeg', 'data': img_bytes.getvalue()}])
                    
                    # Limpieza y auto-guardado
                    match = re.search(r'\[.*\]', response.text, re.DOTALL)
                    if match:
                        df = pd.read_json(io.StringIO(match.group()))
                        # GUARDADO AUTOMÁTICO EN LA BASE DE DATOS
                        conn = conectar()
                        df.to_sql('auditoria', conn, if_exists='append', index=False)
                        conn.close()
                        st.success(f"✅ Se han procesado y guardado {len(df)} filas automáticamente.")
                        st.dataframe(df)
                    else:
                        st.error("No pude leer la tabla. Asegúrate de que la foto esté derecha.")
                except Exception as e:
                    st.error("Error de comunicación con el cerebro IA.")

# --- 5. REGISTROS HISTÓRICOS ---
elif menu == "📖 REGISTROS":
    st.title("📖 Base de Datos Consolidada")
    df = pd.read_sql_query("SELECT * FROM auditoria", conectar())
    st.dataframe(df, use_container_width=True)
    
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Todo (Excel)", data=csv, file_name="reporte_sga.csv")

elif menu == "👥 Personal":
    st.title("👥 Registro de Socios")
    with st.form("p"):
        n = st.text_input("Nombre").upper(); c = st.text_input("CI")
        if st.form_submit_button("Guardar"):
            conn = conectar(); conn.execute("INSERT INTO personal (nombre, ci) VALUES (?,?)", (n, c))
            conn.commit(); conn.close(); st.success("Registrado.")
    st.dataframe(pd.read_sql_query("SELECT * FROM personal", conectar()))

else:
    st.title("📊 Dashboard")
    st.write("Estado del sistema: **Activo y en la Nube.**")
