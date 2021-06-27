from dataclasses import dataclass


@dataclass
class Nutrients:
    hunger: int

    def __mul__(self, number: int) -> "Nutrients":
        return Nutrients(self.hunger * number)
