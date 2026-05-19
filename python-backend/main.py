import uvicorn
from dotenv import load_dotenv
from api_controller import APIController

# 1. Cargar obligatoriamente configuraciones locales (si trabajas en desarrollo).
# Esto hidratará os.environ antes de que ninguna clase sea instanciada.
load_dotenv()

# 2. Instanciamos el Controlador de la Arquitectura, el cual compone las clases internamente.
controller = APIController()

# 3. Exportamos el motor de FastAPI para ASGI/Uvicorn
app = controller.app

if __name__ == "__main__":
    # Comando de ejecución que se lanzará si ejecutas `python main.py`
    print("Iniciando servicio de Asistente Conversacional Neurosimbólico...")
    # NOTA: En este MVP habilitamos "reload=True" para poder desarrollar más rápido
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
