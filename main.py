#Twilio has not given me text permissions.

import os
from agent_preamble import agent_preamble, base_message
from enum import Enum
from typing import Type
from loguru import logger
from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic.v1 import BaseModel, Field


from vocode.logging import configure_pretty_logging
from vocode.streaming.action.base_action import BaseAction
from vocode.streaming.action.end_conversation import EndConversationVocodeActionConfig, EndConversation
from vocode.streaming.agent.base_agent import BaseAgent
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.models.actions import ActionConfig, ActionInput, ActionOutput, FunctionCallActionTrigger
from vocode.streaming.models.agent import AgentConfig, ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.telephony import TwilioConfig
from vocode.streaming.models.transcriber import DeepgramTranscriberConfig
from vocode.streaming.telephony.config_manager.redis_config_manager import RedisConfigManager
from vocode.streaming.telephony.server.base import TelephonyServer, TwilioInboundCallConfig
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramEndpointingConfig

load_dotenv()
configure_pretty_logging()

app = FastAPI(docs_url=None)
config_manager = RedisConfigManager()

BASE_URL = os.getenv("BASE_URL")

actually_send_sms = False #Twilio has not given permission to send sms, haven't tested sms functionality

# async def end_of_call_event():
#     logger.critical("Call ended, sending SMS")
#     action_input = ActionInput(params=TwilioSendSmsParameters(to='recipient_number', body='Call has ended'))
#     sms_action = TwilioSendSms(action_config=TwilioSendSmsActionConfig())
#     await sms_action.run(action_input)


# end_conversation_action = EndConversationVocodeActionConfig(
#     type="action_end_conversation",
#     action_trigger=FunctionCallActionTrigger(
#         type="action_trigger_function_call",
#         function_to_call=end_of_call_event
#     )
# )

def log_sms_content(to: str, body: str):
    logger.critical(f"Simulating SMS to: {to}, Body: {body}")


class MyActionType(str, Enum):
    TWILIO_SEND_SMS = "twilio_send_sms"

class MyAgentType(str, Enum):
    MY_CHAT_GPT = "my_agent_chat_gpt"



class MyActionFactory:
    def create_action(self, action_config: ActionConfig) -> BaseAction:
        if isinstance(action_config, TwilioSendSmsActionConfig):
            return TwilioSendSms(action_config=action_config, should_respond=True)
        elif isinstance(action_config, EndConversationVocodeActionConfig):
            return EndConversation(action_config=action_config)
        else:
            raise Exception("Invalid custom action type")

class TwilioSendSmsActionConfig(ActionConfig, type=MyActionType.TWILIO_SEND_SMS):
    pass


class TwilioSendSmsParameters(BaseModel):
    to: str = Field(..., description="The mobile number of the recipient.")
    body: str = Field(..., description="The Time and Date selected for the appointment and the Doctor that they will see.")

class TwilioSendSmsResponse(BaseModel):
    success: bool
    message: str


class TwilioSendSms(BaseAction [TwilioSendSmsActionConfig, TwilioSendSmsParameters, TwilioSendSmsResponse] ):
    description: str = "Sends an sms."
    parameters_type: Type[TwilioSendSmsParameters] = TwilioSendSmsParameters
    response_type: Type[TwilioSendSmsResponse] = TwilioSendSmsResponse
    
    if not actually_send_sms:
        async def run(self, action_input: ActionInput[TwilioSendSmsParameters]) -> ActionOutput[TwilioSendSmsResponse]:
            log_sms_content(action_input.params.to, action_input.params.body)
            return ActionOutput(
                action_type=self.action_config.type,
                response=TwilioSendSmsResponse(
                    success=True, message="Successfully simulated sending SMS."
                ),
            )
    else:
        async def run(
            self, action_input: ActionInput[TwilioSendSmsParameters]) -> ActionOutput[TwilioSendSmsResponse]:
            from twilio.rest import Client

            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token  = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_FROM_NUMBER")
            # to_number   = os.getenv("TWILIO_TO_NUMBER") #hardcoded

            try:
                client = Client(account_sid, auth_token)
                logger.critical(f"Sending SMS to: {action_input.params.to}, Body: {action_input.params.body}")
                message = client.messages.create(
                    from_=from_number,
                    body=action_input.params.body,
                    to="+1{}".format(action_input.params.to),
                    # to=to_number.format(action_input.params.to), #swap this with above to hardcode number
                )

                return ActionOutput(
                    action_type=self.action_config.type,
                    response=TwilioSendSmsResponse(success=True, message="Successfully sent SMS."),
                )

            except RuntimeError as e:
                logger.debug(f"Failed to send SMS: {e}")
                return ActionOutput(action_type=self.action_config.type,
                    response=TwilioSendSmsResponse(success=False, message="Failed to send SMS"),
                )


class MyChatGPTAgentConfig(ChatGPTAgentConfig, type=MyAgentType.MY_CHAT_GPT.value):
    pass


class MyChatGPTAgent(ChatGPTAgent):
    def __init__(
        self,
        agent_config: MyChatGPTAgentConfig,
        action_factory: MyActionFactory = MyActionFactory(),
    ):
        super().__init__(agent_config, action_factory=action_factory)


class MyAgentFactory:
    def create_agent(self, agent_config: AgentConfig) -> BaseAgent:
        if isinstance(agent_config, MyChatGPTAgentConfig):
            return MyChatGPTAgent(agent_config=agent_config)
        else:
            raise Exception("Invalid custom agent config", agent_config.type)


synthesizer_config=ElevenLabsSynthesizerConfig.from_telephone_output_device(
    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
    voice_id=os.getenv("ELEVEN_LABS_VOICE_ID"),
)

transcriber_config = DeepgramTranscriberConfig.from_telephone_input_device(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    endpointing_config=DeepgramEndpointingConfig()
)

agent_config = MyChatGPTAgentConfig(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    initial_message=BaseMessage(text=base_message),
    prompt_preamble=agent_preamble,
    generate_responses=True,
    actions=[
        TwilioSendSmsActionConfig(), 
        # end_conversation_action
    ],
    end_conversation_on_goodbye=True,
)


telephony_server = TelephonyServer(
    agent_factory=MyAgentFactory(),
    base_url=BASE_URL,
    config_manager=config_manager,
    inbound_call_configs=[
        TwilioInboundCallConfig(
            synthesizer_config=ElevenLabsSynthesizerConfig.from_telephone_output_device(
                api_key=os.getenv("ELEVEN_LABS_API_KEY"),
                voice_id=os.getenv("ELEVEN_LABS_VOICE_ID"),
            ),
            url="/inbound_call",
            agent_config=agent_config,
            twilio_config=TwilioConfig(
                account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            ),
            transcriber_config=transcriber_config,
        )
    ],
)

app.include_router(telephony_server.get_router())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)


