from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .TBLSchema import TBLSchema


class TBLSchemaBuilder(ABC):
    @abstractmethod
    def build(self, data: dict[str, Any]) -> TBLSchema:
        pass