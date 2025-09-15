from typing import Protocol


class OTPProvider(Protocol):
    def send(self, phone: str) -> str:
        ...

    def verify(self, phone: str, code: str) -> bool:
        ...


