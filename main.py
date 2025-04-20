from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
import uvicorn

if __name__ == "__main__":
    app = FastAPI()
    
    # Configure CORS middleware to allow any origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow requests from any origin
        allow_credentials=False,  # Must be False when using wildcard origins
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    
    # Include the common API router with a global prefix
    app.include_router(api_router, prefix="/api")
    
    uvicorn.run(app, host="0.0.0.0", port=3000)
