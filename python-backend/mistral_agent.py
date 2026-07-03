import os
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_mistralai.chat_models import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import StructuredTool

from drools_service import DroolsService

# Esquema para forzar al LLM a recolectar exactamente esta estructura antes de llamar a la herramienta
class LoanData(BaseModel):
    age: int = Field(description="La edad del solicitante")
    income: float = Field(description="Los ingresos anuales del solicitante")
    loan_amount: float = Field(description="El monto del préstamo bancario solicitado")


class MistralAgent:
    """
    Agente conversacional que integra Mistral AI (LLM) con LangChain.
    Se encarga de mantener la memoria (turns) y accionar la herramienta del DroolsService.
    """
    def __init__(self):
        # 1. Validación de variables de entorno críticas
        self.api_key = os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("ERROR: La variable MISTRAL_API_KEY no está configurada (revisa .env)")

        # 2. Instanciación del Modelo LLM (Mistral-Small es rápido y eficaz para tooling)
        self.llm = ChatMistralAI(
            mistral_api_key=self.api_key,
            model="mistral-small-latest",
            temperature=0.2  # Baja creatividad para que respete las instrucciones rígidamente
        )
        
        # 3. Componentes de la Arquitectura
        self.drools_service = DroolsService()
        self._setup_tools()
        self._setup_agent_executor()
        
        # Memoria conversacional simplificada
        # En un backend multi-usuario real, esto sería un Storage externo clave-valor (ej. Redis) usando el user_id
        self.memory = []

    def _setup_tools(self):
        """
        Define la Tool (Function Calling) que LangChain expondrá al LLM.
        Vincula nuestra clase asíncrona de conectividad con la abstracción del Tool.
        """
        self.drools_tool = StructuredTool.from_function(
            coroutine=self._invoke_drools,
            name="evaluate_loan",
            description=(
                "Utiliza OBLIGATORIAMENTE esta herramienta para evaluar si el usuario califica para un préstamo bancario. "
                "Requiere recopilar primero todos los campos obligatorios definidos en el esquema."
            ),
            args_schema=LoanData
        )
        self.tools = [self.drools_tool]

    def _setup_agent_executor(self):
        """
        Configura el Sistema de Prompting y el pipeline de ejecución del Agente.
        """
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "Eres un asistente conversacional de un banco. Tu trabajo es ayudar a los usuarios "
             "a conocer si su solicitud de préstamo sería aprobada. "
             "Para ello, DEBES usar la herramienta 'evaluate_loan'. "
             "REGLA CRUCIAL: No puedes inventar datos. Si la herramienta requiere campos/información que el "
             "usuario aún no te ha proporcionado en la conversación, pregúntale educadamente por los datos faltantes. "
             "Una vez que tengas todos los datos requeridos por el esquema de la herramienta, llámala y resume su respuesta al usuario."
            ),
            # Inyección de memoria para contexto de la conversación
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            # Memoria interna auxiliar para los pasos intermedios de los Actions
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Se crea el agente preparado para usar "Tools" y un orquestador que gestiona sus ciclos
        agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    async def _invoke_drools(self, **kwargs) -> str:
        """
        Wrapper interno de la Tool. El LLM extraerá los datos en JSON, LangChain pasará kwargs a este método,
        y este método invocará el servicio de conexión REST enviando directamente el diccionario de datos.
        """
        print('datos: ',kwargs)
        result = await self.drools_service.evaluate_loan_rules(kwargs)
        # Se devuelve en formato de cadena para que el LLM lo pueda razonar nativamente
        return str(result)

    async def process_message(self, user_input: str) -> str:
        """
        Punto de entrada principal. Recibe texto, invoca al agente, actualiza heurística de memoria
        y retorna la cadena final evaluada por el LLM.
        """
        response = await self.agent_executor.ainvoke({
            "input": user_input,
            "chat_history": self.memory
        })
        
        output_text = response["output"]

        # Agregamos la interacción a la memoria para el próximo turno
        self.memory.append(("human", user_input))
        self.memory.append(("ai", output_text))

        return output_text
