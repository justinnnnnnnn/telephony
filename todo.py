#In addition to sms privileges

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