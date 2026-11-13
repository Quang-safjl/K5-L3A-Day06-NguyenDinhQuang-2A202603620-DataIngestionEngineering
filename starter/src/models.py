from dataclasses import dataclass, field
from typing import Any

@dataclass
class DocumentPage:
    document_id: str
    source: str
    page: str          # RST không phân trang: page = ID đơn vị
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    source: str
    page: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)