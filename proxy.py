from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from fastapi import FastAPI
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse
app = FastAPI()

# Define the target server URL
TARGET_SERVER = "-----"

client = httpx.AsyncClient(timeout=None)




class ReverseProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Check if the path matches an endpoint in the mapping
                # Forward the request to the target server
        target_url = f"{TARGET_SERVER}{request.url.path}"
        headers=dict(request.headers)
        headers.update({
            "apikey": "-----",
            "host": "---------"
        })
        req = client.build_request(request.method, target_url, headers=headers, data=await request.body())
        r = await client.send(req, stream=True)
                # Return the response to the client
        return StreamingResponse(r.aiter_text(), background=BackgroundTask(r.aclose))


# Add reverse proxy middleware to the app
app.add_middleware(ReverseProxyMiddleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="------", port=8000)
