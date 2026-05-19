import os
import httpx

class DroolsService:
    """
    Servicio para manejar la comunicación HTTP con el motor de reglas lógicas (Drools).
    Aísla la lógica de red y configuración de la API externa siguiendo principios SOLID.
    """
    def __init__(self):
        # Cargamos la URL del motor de reglas desde las variables de entorno.
        # Si no se define, apuntará al contenedor local por defecto.
        self.drools_url = os.environ.get("DROOLS_URL", "http://localhost:8080/api/evaluate")

    async def evaluate_loan_rules(self, data: dict) -> dict:
        """
        Envía los datos procesados por el LLM hacia Drools para su evaluación.
        
        Args:
            data (dict): Diccionario con las claves esperadas por Drools (ej. 'age', 'income', 'loan_amount').
            
        Returns:
            dict: Respuesta parseada de Drools (ej. {"status": "APROBADO", "reason": "..."})
        """
        try:
            async with httpx.AsyncClient() as client:
                # Se envía el payload en formato JSON como requiere la consigna
                response = await client.post(self.drools_url, json=data)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            # En caso de caída del contenedor Drools, devolvemos un status seguro
            # para que el LLM pueda informar al usuario del fallo sin romperse.
            print(f"[DroolsService] Error de red al conectar con Drools: {e}")
            return {
                "status": "ERROR", 
                "reason": "El motor de reglas lógicas no está disponible en este momento."
            }
