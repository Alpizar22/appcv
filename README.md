# Analizador de CVs con IA

App Streamlit para reclutadores que analiza CVs en PDF con Claude (Anthropic) y devuelve:

- **Score general** (0–100)
- **Habilidades** técnicas, blandas e idiomas
- **Red flags** detectadas
- **Puntos fuertes**
- **Veredicto ejecutivo** en texto
- **Recomendación**: CONTRATAR / ENTREVISTAR / DESCARTAR

---

## Ejecución local

### 1. Clonar/descargar el proyecto

```bash
git clone <url-del-repo>
cd appcv
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar la API key

Copia `.env.example` a `.env` y pega tu API key de Anthropic:

```bash
cp .env.example .env
```

Edita `.env`:

```
ANTHROPIC_API_KEY=sk-ant-api03-TU_CLAVE_AQUI
```

Obtén tu API key en: https://console.anthropic.com/

### 4. Ejecutar la app

```bash
streamlit run app.py
```

La app abre en `http://localhost:8501`.

---

## Despliegue en Streamlit Cloud

### Requisitos previos

- Cuenta en [Streamlit Cloud](https://streamlit.io/cloud) (gratuita)
- Repositorio en GitHub con el código

### Pasos

1. **Sube el proyecto a GitHub** (sin el archivo `.env`):

   ```bash
   git init
   git add app.py requirements.txt README.md .env.example
   git commit -m "Initial commit"
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   git push -u origin main
   ```

   > **Importante:** nunca subas el `.env` con tu API key real. Añádelo a `.gitignore`.

2. **Crea la app en Streamlit Cloud:**
   - Ve a [share.streamlit.io](https://share.streamlit.io)
   - Haz clic en **"New app"**
   - Selecciona tu repositorio y la rama `main`
   - En **"Main file path"** escribe `app.py`
   - Haz clic en **"Advanced settings"**

3. **Configura el secreto:**
   - En "Secrets", añade:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-api03-TU_CLAVE_AQUI"
     ```
   - Haz clic en **"Save"**

4. Haz clic en **"Deploy"**. En 1-2 minutos la app estará disponible en una URL pública.

### Nota sobre secretos en Streamlit Cloud

Streamlit Cloud inyecta los secretos como variables de entorno, por lo que `os.getenv("ANTHROPIC_API_KEY")` los lee automáticamente sin necesidad de `.env`.

---

## Estructura del proyecto

```
appcv/
├── app.py            # Código principal de la app
├── requirements.txt  # Dependencias Python
├── .env              # API key local (NO subir a Git)
├── .env.example      # Plantilla de variables de entorno
└── README.md         # Este archivo
```

---

## Salida JSON del análisis

```json
{
  "score_general": 82,
  "habilidades": {
    "tecnicas": ["Python", "FastAPI", "PostgreSQL", "Docker"],
    "blandas": ["Liderazgo de equipo", "Comunicación efectiva"],
    "idiomas": ["Español - Nativo", "Inglés - B2"]
  },
  "puntos_fuertes": [
    "Más de 5 años de experiencia en backend",
    "Stack técnico alineado con el puesto"
  ],
  "red_flags": [
    "No se menciona experiencia con AWS",
    "Historial con cambios frecuentes de empresa"
  ],
  "veredicto_ejecutivo": "Candidato sólido con experiencia relevante...",
  "recomendacion": "ENTREVISTAR"
}
```
