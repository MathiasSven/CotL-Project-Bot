import configparser
import os

directory = os.path.dirname(os.path.realpath(__file__))


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

    def get(self, section, key):
        return self.config.get(section, key)
