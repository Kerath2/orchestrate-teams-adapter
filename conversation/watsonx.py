import requests
import logging
from session.chat.base_session import ChatBaseSessionManager
from .watsonx_token_manager import WatsonxTokenManager
from .watsonx_settings import WatsonxSettings

logger = logging.getLogger(__name__)

class WatsonxOrchestrate:
    def __init__(
            self, 
            chat_session_manager: ChatBaseSessionManager,
            settings: WatsonxSettings,
            token_manager: WatsonxTokenManager
        ):
        """
        :param chat_session_manager: Instance of ChatBaseSessionManager to manage chat sessions.
        :param settings: Instance of WatsonxSettings for configuration.
        :param token_manager: Instance of WatsonxTokenManager to manage tokens.
        """
        self.chat_session = chat_session_manager
        self.token_manager = token_manager
        self.settings = settings
   
    def chat_completion(self, conversation_id: str, user_message: str, context):
        """
        Call Watson API with user message.
        
        :param conversation_id: Unique identifier for the conversation.
        :param user_message: Message from the user.
        :param context: Additional context for the conversation.
        """
        api_url = f"{self.settings.base_url}/v1/orchestrate/{self.settings.agent_id}/chat/completions"
        token = self.token_manager.get_token()
        logger.info("Starting chat_completion conversation_id=%s", conversation_id)
        
        headers = {
            'Authorization': f'Bearer {token}',
            'accept': 'application/json',
            'content-type': 'application/json'
        }

        thread_id = self.chat_session.get_thread(conversation_id)
        if thread_id:
            headers['X-IBM-THREAD-ID'] = thread_id
            logger.debug("Using existing thread %s for conversation_id=%s", thread_id, conversation_id)
        else:
            logger.debug("No previous thread for conversation_id=%s, requesting a new one.", conversation_id)

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            "context": context,
            "stream": False
        }
        logger.debug("Payload sent to Watson: %s", payload)
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            logger.info(
                "Call to Watson completed conversation_id=%s status=%s",
                conversation_id,
                response.status_code
            )
            response.raise_for_status()
            result = response.json()

            logger.debug("Response received from Watson for conversation_id=%s: %s", conversation_id, result)

            new_thread_id = result.get('thread_id')
            if new_thread_id:
                self.chat_session.save_thread(conversation_id, new_thread_id)
                logger.debug("Thread %s stored for conversation_id=%s", new_thread_id, conversation_id)
            
            if result and 'choices' in result and len(result['choices']) > 0:
                assistant_message = result['choices'][0]['message']['content']
                logger.debug("Response received for conversation_id=%s: %s", conversation_id, assistant_message)
                return assistant_message
            else:
                logger.warning("Empty response from Watson for conversation_id=%s", conversation_id)
                return None
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(
                    "HTTP error when calling Watson conversation_id=%s status=%s body=%s",
                    conversation_id,
                    e.response.status_code,
                    e.response.text
                )
            logger.exception("Request to Watson failed for conversation_id=%s", conversation_id)
            return None
