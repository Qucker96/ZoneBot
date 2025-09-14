import os
from pathlib import Path
from utils.tomlIO import TomlIO


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Конфиги
admin = TomlIO(os.path.join(BASE_DIR, "src","data", "admin.toml"))