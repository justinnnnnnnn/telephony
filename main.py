#this implementation only talks to receptionist, doesn't contain the custom agent and action middleware to then send a confirmation text
import os
from agent_preamble import agent_preamble, base_message

from dotenv import load_dotenv
from fastapi import FastAPI
from vocode.logging import configure_pretty_logging
from vocode.streaming.models.agent import ChatGPTAgentConfig
from vocode.streaming.models.message import BaseMessage
from vocode.streaming.models.telephony import TwilioConfig
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.transcriber import DeepgramTranscriberConfig
from vocode.streaming.telephony.config_manager.redis_config_manager import RedisConfigManager
from vocode.streaming.telephony.server.base import TelephonyServer, TwilioInboundCallConfig
from vocode.streaming.transcriber.deepgram_transcriber import DeepgramEndpointingConfig


load_dotenv()
configure_pretty_logging()

app = FastAPI(docs_url=None)
config_manager = RedisConfigManager()

BASE_URL = os.getenv("BASE_URL")


synthesizer_config=ElevenLabsSynthesizerConfig.from_telephone_output_device(
    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
    voice_id=os.getenv("ELEVEN_LABS_VOICE_ID"),
)

transcriber_config = DeepgramTranscriberConfig.from_telephone_input_device(
    api_key=os.getenv("DEEPGRAM_API_KEY"),
    endpointing_config=DeepgramEndpointingConfig()
)


telephony_server = TelephonyServer(
    base_url=BASE_URL,
    config_manager=config_manager,
    inbound_call_configs=[
        TwilioInboundCallConfig(
            synthesizer_config=ElevenLabsSynthesizerConfig.from_telephone_output_device(
                api_key=os.getenv("ELEVEN_LABS_API_KEY"),
                voice_id=os.getenv("ELEVEN_LABS_VOICE_ID"),
            ),
            url="/inbound_call",
            agent_config=ChatGPTAgentConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                initial_message=BaseMessage(text=base_message),
                prompt_preamble=agent_preamble,
                generate_responses=True,
                model_name="gpt-4o"
            ),
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


