import configparser
import os

directory = os.path.dirname(os.path.realpath(__file__))


class Config:
    def __init__(self):
        self.config = configparser.RawConfigParser()
        self.config.optionxform = str
        self.config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

    def get(self, section, key):
        return self.config.get(section, key)

    def dict_set(self, section: str, keys: dict):
        with open(f"{os.path.join(directory, os.pardir)}/config.ini", "w") as f:
            for key in keys:
                self.config.set(section, key, keys[key])
            self.config.write(f)
            return


with open(f"{directory}/codenames", 'r') as codenames:
    codenames = codenames.read().splitlines()