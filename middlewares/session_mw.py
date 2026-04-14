from langchain.agents.middleware import SummarizationMiddleware

model = init_chat_model('gpt-4.1-mini')

summary_model = init_chat_model('gpt-4.1-mini')
summary_middleware = SummarizationMiddleware(
    model = summary_model,
    trigger = ('tokens', 1000), # 요약이 진행되어야 할 최소 토큰 수
    keep = ('messages', 1),     # 요약에 포함되지 않을 최근 메세지 수
    summary_prompt = '대화내역을 한국어로 적절히 요약해 주세요.\n\n{messages}'  # {messages} 필수!
)

agent = create_agent(
    model=model,
    tools=[],
    checkpointer=InMemorySaver(),
    middleware = [summary_middleware]   # 여러 개 가능
)

# 대화내역 쌓기
response = agent.invoke(
    input={'messages': [('human', '뮤지컬 Wicked의 내용을 Elphaba입장에서 서술해줘. Elphaba역으로 연극에 출연해야 해. 중요한 포인트들을 짚어줘~')]},
    config={'configurable': {'thread_id': '100'}}
)
pprint(response)
print(response['messages'][-1].content)
print('---------------\n')

response = agent.invoke(
    input={'messages': [('human', 'Elphama가 Glinda를 어떤 심정으로 보는 게 좋을까?')]},
    config={'configurable': {'thread_id': '100'}}
)
pprint(response)
print(response['messages'][-1].content)
print('---------------\n')

response = agent.invoke(
    input={'messages': [('human', '또 연기할 때 신경 써야 할 게 있을까? ')]},
    config={'configurable': {'thread_id': '100'}}
)
pprint(response)
print(response['messages'][-1].content)
print('---------------\n')