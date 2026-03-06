"""Start the Clara AI Pipeline API with Swagger UI at http://localhost:8000/docs"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
