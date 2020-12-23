import configparser
import os

directory = os.path.dirname(os.path.realpath(__file__))


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

    def get(self, section, key):
        return self.config.get(section, key)

    def dict_set(self, section: str, keys: dict):
        self.config[section] = keys
        self.config.write(f"{os.path.join(directory, os.pardir)}/config.ini")
        return


with open(f"{directory}/codenames", 'r') as codenames:
    codenames = codenames.read().splitlines()