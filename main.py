from mind import mind
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from schema import Message

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/assessment")
def mind_assessment(response: Message):
    return mind(response)
