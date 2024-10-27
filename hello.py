from types import TracebackType
from typing import Optional, Type
import websockets.asyncio.client
import asyncio
import logging
import sys
import random

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Connection:
    websocket: websockets.asyncio.client.ClientConnection
    inbox: asyncio.Queue
    outbox: asyncio.Queue
    loop_task: asyncio.Task

    def __init__(self) -> None:
        self.websocket = None
        self.inbox = asyncio.Queue()
        self.outbox = asyncio.Queue()
        self.loop_task = None

    async def __aenter__(self) -> "Connection":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.loop_task:
            await self.loop_task
        if self.websocket:
            await self.websocket.close()

    async def connect(self, hostname: str, port: str) -> None:
        self.websocket = await websockets.asyncio.client.connect(
            f"ws://{hostname}:{port}"
        )
        self.loop_task = asyncio.create_task(self.loop())

    async def produce(self) -> None:
        while True:
            message = await self.outbox.get()
            await self.websocket.send(message)
            logging.debug("sent from outbox")

    async def consume(self) -> None:
        async for message in self.websocket:
            await self.inbox.put(message)
            logging.debug("received to inbox")

    async def loop(self) -> None:
        await asyncio.gather(self.consume(), self.produce())


class Subscriber:
    connection: Connection
    loop_task: asyncio.Task

    def __init__(self, connection: Connection):
        self.connection = connection
        self.loop_task = None

    async def __aenter__(self) -> "Subscriber":
        self.loop_task = asyncio.create_task(self.consume())
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if self.loop_task:
            await self.loop_task

    async def consume(self) -> None:
        while True:
            message = await self.connection.inbox.get()
            logging.debug("received from inbox")
            print(message)

    async def send_something(self, message: str) -> None:
        await self.connection.outbox.put(message)
        logging.debug("sent to outbox")


async def main():
    async with Connection() as connection:
        await connection.connect("127.0.0.1", "4444")
        async with Subscriber(connection) as subscriber:

            async def foo(wait: int):
                await subscriber.send_something(str(wait))

            asyncio.gather(*[foo(i) for i in range(5)])
            return


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main(), debug=True))
    except asyncio.CancelledError as e:
        print(f"main() was cancelled: {e}")
    except KeyboardInterrupt as _:
        print("Received KeyboardInterrupt - shutting down")
