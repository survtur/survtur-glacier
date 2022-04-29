from typing import TypedDict


class VaultDict(TypedDict):
    VaultARN: str
    VaultName: str
    CreationDate: str
    LastInventoryDate: str
    NumberOfArchives: int
    SizeInBytes: int
