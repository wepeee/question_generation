# QUESTION_GENERATION/utils/load_env.py
from dotenv import load_dotenv, find_dotenv

def run_load_env() -> None:
    """
    Muat variabel dari file .env (jika ada) menggunakan python-dotenv.
    Panggil sekali di awal program (mis. di main.py).
    """
    load_dotenv(find_dotenv())
