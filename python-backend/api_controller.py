from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from mistral_agent import MistralAgent

class APIController:
    """
    Clase responsable de inicializar la API (FastAPI) y definir los endpoints.
    Controla el enrutamiento HTTP y el ciclo de vida de la aplicación.
    """
    def __init__(self):
        self.app = FastAPI(
            title="Asistente Bancario Neurosimbólico",
            description="API para interactuar con Mistral LLM y Drools.",
            version="1.0.0"
        )
        self.agent = None  # Se inicializa de forma lazy durante el startup
        self._setup_routes()

    def _setup_routes(self):
        """
        Definición y registro de Eventos y Endpoints de la API.
        """
        
        @self.app.on_event("startup")
        async def on_startup():
            # Patrón de diseño para diferir las cargas pesadas o validaciones al levantar el servidor
            print("Inicializando MistralAgent...")
            self.agent = MistralAgent()
            print("MistralAgent listo para recibir operaciones.")


        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            # Plantilla estática HTML + JS incrustada para servir rápidamente la interfaz MVP a los usuarios,
            # cumpliendo el requisito de no usar frameworks SPA para esta prueba.
            html_content = """
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Conversación Bancaria</title>
                <style>
                    body { font-family: 'Inter', -apple-system, sans-serif; background: #eef2f5; margin: 0; padding: 20px; display: flex; justify-content: center; }
                    .chat-container { width: 100%; max-width: 600px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); display: flex; flex-direction: column; overflow: hidden;height: 85vh; }
                    .header { background: #1664C0; color: white; padding: 20px; text-align: center; }
                    .header h2 { margin: 0; font-size: 1.2rem;}
                    #chatbox { flex: 1; padding: 20px; overflow-y: auto; background: #f9f9f9; display: flex; flex-direction: column; gap: 15px;}
                    .msg { padding: 14px 18px; border-radius: 12px; line-height: 1.5; font-size: 0.95rem; max-width: 80%; animation: fadeIn 0.3s; box-shadow: 0 1px 3px rgba(0,0,0,0.05);}
                    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                    .user { background: #d1e7dd; color: #0f5132; align-self: flex-end; border-bottom-right-radius: 4px; }
                    .bot { background: white; border: 1px solid #dee2e6; color: #212529; align-self: flex-start; border-bottom-left-radius: 4px; }
                    .input-area { padding: 15px; background: white; border-top: 1px solid #eee; display: flex; gap: 10px; }
                    #userInput { flex: 1; padding: 14px; border: 1px solid #ccc; border-radius: 8px; font-size: 1rem; outline: none; transition: border 0.2s;}
                    #userInput:focus { border-color: #1664C0; }
                    button { padding: 14px 24px; background: #1664C0; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; font-weight: 600; transition: background 0.2s;}
                    button:hover { background: #104a8e; }
                    .loading { font-size: 0.85rem; color: #6c757d; font-style: italic; align-self: flex-start;}
                </style>
            </head>
            <body>
                <div class="chat-container">
                    <div class="header">
                        <h2>Asistente Bancario Inteligente</h2>
                    </div>
                    <div id="chatbox">
                        <div class="msg bot">👋 Hola, soy tu asistente bancario. Puedo ayudarte a realizar la evaluación lógica para conocer si tu préstamo es aprobado. ¿En qué te puedo ayudar?</div>
                    </div>
                    <div class="input-area">
                        <input type="text" id="userInput" placeholder="Ej. Quiero solicitar un préstamo..." onkeydown="if(event.key === 'Enter') sendMessage()"/>
                        <button id="sendBtn" onclick="sendMessage()">Enviar</button>
                    </div>
                </div>

                <script>
                    async function sendMessage() {
                        const input = document.getElementById("userInput");
                        const txt = input.value.trim();
                        if (!txt) return;

                        const chatbox = document.getElementById("chatbox");
                        const btn = document.getElementById("sendBtn");
                        
                        // Añadir mensaje del usuario
                        chatbox.innerHTML += `<div class="msg user">${txt}</div>`;
                        input.value = "";
                        input.disabled = true;
                        btn.disabled = true;
                        
                        // Añadir indicador temporal de escritura
                        const loadingId = "load-" + Date.now();
                        chatbox.innerHTML += `<div class="loading" id="${loadingId}">El asistente está pensando...</div>`;
                        chatbox.scrollTop = chatbox.scrollHeight;

                        try {
                            const response = await fetch("/chat", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ message: txt })
                            });
                            
                            const data = await response.json();
                            document.getElementById(loadingId).remove(); // Quitar loading
                            
                            // Añadir respuesta
                            const formattedReply = data.reply.replace(/\\n/g, '<br>');
                            chatbox.innerHTML += `<div class="msg bot">${formattedReply}</div>`;
                        } catch(err) {
                            document.getElementById(loadingId).remove();
                            chatbox.innerHTML += `<div class="msg bot" style="color:#dc3545;">⚠️ Error de conexión con el agente. Asegurate de configurar tu MISTRAL_API_KEY.</div>`;
                        }
                        
                        chatbox.scrollTop = chatbox.scrollHeight;
                        input.disabled = false;
                        btn.disabled = false;
                        input.focus();
                    }
                </script>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)


        class ChatRequest(BaseModel):
            message: str

        @self.app.post("/chat")
        async def post_chat(req: ChatRequest):
            """
            Endpoint CORE: Recibe el payload del front, lo inyecta en el objeto MistralAgent
            y orquesta la respuesta final.
            """
            try:
                reply_text = await self.agent.process_message(req.message)
                return {"reply": reply_text}
            except Exception as e:
                return {"reply": f"Lo siento, ocurrió un error procesando tu consulta: {str(e)}"}
