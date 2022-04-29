from typing import TypedDict


class Archive(TypedDict):
    ArchiveDescription: str
    ArchiveId: str
    CreationDate: str
    SHA256TreeHash: str
    Size: int
