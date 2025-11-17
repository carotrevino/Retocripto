# Consultorio | App Streamlit (on-prem)
Pasos básicos:
1) Crea y activa entorno virtual
2) `pip install -r requirements.txt`
3) Ejecuta: `streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0`
4) Accede en el navegador: `http://localhost:8501` o `http://IP_LOCAL:8501`

Archivos:
- `app_core.py`: lógica de cifrado (Fernet), CSV y operaciones.
- `streamlit_app.py`: interfaz Streamlit con login básico y tabs por rol.
- `requirements.txt`: dependencias
- `.gitignore`: ignora secretos y datos
