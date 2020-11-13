from setuptools import setup
from os import path
from shutil import copy
import configparser

folder = path.dirname(path.realpath(__file__))

__version__ = "1.0"

print("Original Repository: https://github.com/MathiasSven/CotL-Project-Bot")
print(f"Version: {__version__}")
print("License: GPL-3.0\n")

copy(f"{folder}/config.ini.sample", "f{folder}/config.ini")

# config = configparser.ConfigParser()
# config.read("{folder}/config.ini")
# config["server"]["TOKEN"] = token
# config["server"]["API_KEY"] = prefix
# config["server"]["PREFIX"] = name
# config["server"]["ADMIN_ID"] = logo
# config["server"]["GUILD_ID"] = system_channel
# config["server"]["AUTO_ROLE_ID"] = colour
# config["server"]["APPLICATIONS_CATEGORY_ID"] = colour
# config["server"]["APPLICATION_CHANNEL_ID"] = colour
# config["server"]["API_URL"] = colour
# config["server"]["COLOUR"] = colour
#
# with open("{folder}/config.ini", "w") as f:
#     config.write(f)

input("Done. You can now start the bot.")
