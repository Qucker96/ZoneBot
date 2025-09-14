import os
import tomllib
import tomli_w

from typing import Dict, Any

class TomlIO:

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)


    def _read(self) -> Dict[str, Any]:
        """Возвращает всё содержимое файла как dict"""
        try:
            with open(self.path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, OSError):
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        """Перезаписывает файл целиком"""
        with open(self.path, "wb") as f:
            tomli_w.dump(data, f)


    @staticmethod
    def _nested_get(data: Dict[str, Any], key: str) -> Any:
        """key = 'section.subkey'"""
        keys = key.split(".")
        for k in keys:
            data = data[k]
        return data

    @staticmethod
    def _nested_set(data: Dict[str, Any], key: str, value: Any) -> None:
        """key = 'section.subkey'"""
        keys = key.split(".")
        current = data
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value

    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение. Если ключ не найден - вернёт default"""
        try:
            data = self._read()
            return self._nested_get(data, key)
        except KeyError:
            return default

    def set(self, key: str, value: Any) -> None:
        """Установить значение по ключу и сохранить файл"""
        data = self._read()
        self._nested_set(data, key, value)
        self._write(data)

    def delete(self, key: str) -> bool:
        """Удалить ключ. Вернёт True, если ключ был удалён"""
        data = self._read()
        keys = key.split(".")
        current = data
        try:
            for k in keys[:-1]:
                current = current[k]
            del current[keys[-1]]
            self._write(data)
            return True
        except KeyError:
            return False