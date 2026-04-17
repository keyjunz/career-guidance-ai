from threading import Lock

from src.agent.state.user_store import UserStore


class UserStoreRegistry:
    _instances: dict[str, UserStore] = {}
    _lock = Lock()

    @classmethod
    def get_store(cls, user_id: str) -> UserStore:
        normalized = user_id.strip()
        if not normalized:
            raise ValueError("user_id is required for user store")

        with cls._lock:
            store = cls._instances.get(normalized)
            if store is None:
                store = UserStore(normalized)
                cls._instances[normalized] = store
            return store
