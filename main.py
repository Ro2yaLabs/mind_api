from mind import mind

import pandas as pd
import os
from fastapi import FastAPI, HTTPException
from typing import List, Dict
from fastapi.middleware.cors import CORSMiddleware
from schema import Message
import sqlite3

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.post("/assessment")
def houda(response: Message):
    return mind(response)
