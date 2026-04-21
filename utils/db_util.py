"""
    FileName: db_util.py
    Location: utils/db_util.py
    Role: DB 관련 객체인데.. 이걸 유틸로 해도 되나.
        PlaceReviewChunkInfo 모델 정의, 데이터 전처리, ChromaDB 연결 및 적재 로직.
"""
from dataclasses import dataclass, asdict

import streamlit as st
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import List
import os
import requests
from sympy import re
from utils.custom_exception import PlaceNotFoundError
from config import Settings
import json

# 벡터 DB 적재 import
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
import hashlib