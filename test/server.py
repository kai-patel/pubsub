import asyncio
import websockets


async def echo(websocket, path):
    async for message in websocket:
        print(f"Echoing: {message}")
        await websocket.send(message)


start_server = websockets.serve(echo, "0.0.0.0", 4444)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
