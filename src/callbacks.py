# src/callbacks.py
from langchain_core.callbacks import BaseCallbackHandler
from queue import Queue
from threading import Event

class StreamingQueueCallbackHandler(BaseCallbackHandler):
    def __init__(self, queue: Queue, stop_event: Event):
        self.queue = queue
        self.stop_event = stop_event

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        if self.stop_event.is_set(): return
        if token:
            # 包装成 dict 放入队列，方便和系统消息区分
            self.queue.put({"type": "token", "content": token})

    def on_llm_error(self, error, **kwargs) -> None:
        self.stop_event.set()