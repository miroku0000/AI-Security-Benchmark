import pickle
import json
import os
from typing import Any, Optional
from pathlib import Path
import gzip

class UserPreferences:
    def __init__(self, preferences_path: str = "user_preferences.pkl.gz"):
        self.preferences_path = preferences_path
        self._cache = None
        self._cache_mtime = None
    
    def save(self, data: Any) -> bool:
        try:
            temp_path = f"{self.preferences_path}.tmp"
            with gzip.open(temp_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(temp_path, self.preferences_path)
            self._cache = data
            self._cache_mtime = os.path.getmtime(self.preferences_path)
            return True
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    
    def load(self) -> Optional[Any]:
        try:
            if os.path.exists(self.preferences_path):
                current_mtime = os.path.getmtime(self.preferences_path)
                if self._cache is not None and self._cache_mtime == current_mtime:
                    return self._cache
                with gzip.open(self.preferences_path, 'rb') as f:
                    data = pickle.load(f)
                self._cache = data
                self._cache_mtime = current_mtime
                return data
            return None
        except Exception:
            return None
    
    def delete(self) -> bool:
        try:
            if os.path.exists(self.preferences_path):
                os.remove(self.preferences_path)
            self._cache = None
            self._cache_mtime = None
            return True
        except Exception:
            return False

class CustomObject:
    def __init__(self, name, value):
        self.name = name
        self.value = value
    
    def __eq__(self, other):
        return isinstance(other, CustomObject) and self.name == other.name and self.value == other.value

def save_preferences(data: Any, filepath: str = "user_preferences.pkl.gz") -> bool:
    prefs = UserPreferences(filepath)
    return prefs.save(data)

def load_preferences(filepath: str = "user_preferences.pkl.gz") -> Optional[Any]:
    prefs = UserPreferences(filepath)
    return prefs.load()

if __name__ == "__main__":
    test_data = {
        "user_id": 12345,
        "username": "john_doe",
        "settings": {
            "theme": "dark",
            "language": "en",
            "notifications": {
                "email": True,
                "push": False,
                "sms": True
            },
            "privacy": {
                "profile_visible": True,
                "share_data": False
            }
        },
        "favorites": ["item1", "item2", "item3"],
        "history": [
            {"timestamp": 1234567890, "action": "login"},
            {"timestamp": 1234567900, "action": "view_profile"}
        ],
        "custom_objects": [
            CustomObject("preference1", 100),
            CustomObject("preference2", "value")
        ],
        "nested_complex": {
            "level1": {
                "level2": {
                    "level3": {
                        "deep_value": 42,
                        "deep_list": [1, 2, 3, {"nested": True}]
                    }
                }
            }
        },
        "mixed_types": [1, "string", 3.14, None, True, {"key": "value"}]
    }
    
    if save_preferences(test_data):
        loaded_data = load_preferences()
        assert loaded_data == test_data
        print("Test passed: Data saved and loaded successfully")