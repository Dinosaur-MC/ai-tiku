from fastapi import FastAPI, Request, Response, status, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

