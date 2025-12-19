import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ANSIBLE_DIR = os.path.join(BASE_DIR, "../ansible")
CONFIG_DIR = os.path.join(BASE_DIR, "../configs")

PUSH_CONFIG_PLAYBOOK = "push_config.yml"
GET_CONFIG_PLAYBOOK = "get_config.yml"

os.makedirs(CONFIG_DIR, exist_ok=True)

LIGHTRAG_URL = {
    "qwen": os.getenv("LIGHTRAG_QWEN_URL"),
    "deepseek": os.getenv("LIGHTRAG_DEEPSEEK_URL"),
    "gemma": os.getenv("LIGHTRAG_GEMMA_URL"),
}

LLAMA_SERVER_URL = {
    "qwen": os.getenv("LLAMA_SERVER_QWEN_URL"),
    "deepseek": os.getenv("LLAMA_SERVER_DEEPSEEK_URL"),
    "gemma": os.getenv("LLAMA_SERVER_GEMMA_URL"),
}
GNS_URL = os.getenv("GNS_URL")
GNS_IP = os.getenv("GNS_IP")

DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")