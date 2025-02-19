from fastapi import FastAPI
from api.router import api_router
import uvicorn

if __name__ == "__main__":

    app = FastAPI()

    # Include the common API router with a global prefix, for example, /api
    app.include_router(api_router, prefix="/api")

    uvicorn.run(app, host="0.0.0.0", port=3000)