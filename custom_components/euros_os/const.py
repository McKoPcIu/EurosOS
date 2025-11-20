"""
===============================================================================
Euros OS Home Assistant Custom Integration
===============================================================================

File        : const.py
Author      : Patryk "KoPcIu" Kopeć / https://github.com/McKoPcIu/EurosOS
Integration : euros_os
Version     : 0.1.0
Description : Custom integration for EurosEnergy and E-On devices.

===============================================================================
"""

DOMAIN = "euros_os"
CONF_KEY = "key"
DEFAULT_KEY = "01010100000000000000"
CONF_IP = "ip"
DEFAULT_IP = "192.168.1.101"

MQTT_PORT = 8883
MQTT_USER = "admin"
MQTT_PASSWORD = "WiosnaJuzToBedaKomary"
MQTT_TIMEOUT = 60


SENSORS_VARIABLES = { # Name, Unit, Icon, Device class
    # Temperture
    "TSM13": ("Temp. obiegu grzewczego (PC)", "°C", "mdi:thermometer", "temperature"),
    "T5fiz": ("Temp. powrotu obiegu grzewczego (PC)", "°C", "mdi:thermometer", "temperature"),
    "SX5": ("Temp. zadana CWU", "°C", "mdi:thermometer", "temperature"),
    "SX6": ("Temp. zadana CO", "°C", "mdi:thermometer", "temperature"),
    "T3fiz": ("Temp. powietrza zasysanego", "°C", "mdi:thermometer", "temperature"),
    "T4fiz": ("Temp. powietrza wyrzucanego", "°C", "mdi:thermometer", "temperature"),
    "TSM15": ("Temp. zbiornika CWU", "°C", "mdi:thermometer", "temperature"),
    "TSM17": ("Temp. zbiornika buforowego", "°C", "mdi:thermometer", "temperature"),
    "TSM10": ("Temp. wewnętrzna", "°C", "mdi:home-thermometer", "temperature"),
    "TSM9": ("Temp. zewnętrzna", "°C", "mdi:home-thermometer-outline", "temperature"),
    "ZM_COIL_TEMP": ("Temp. wyjściowa czynnika", "°C", "mdi:thermometer", "temperature"),
    "TSM16": ("Temp. wejściowa czynnika", "°C", "mdi:thermometer", "temperature"),
    "SX4_PH": ("Próg załączenia ogrzewania", "°C", "mdi:thermometer", "temperature"),
    "TOUT_KOR": ("Temp. zewnętrzna - średnia", "°C", "mdi:thermometer-minus", "temperature"),
    
    # Hetpump data
    "STATE": ("Stan pracy", None, "mdi:sync", None),
    "MODE": ("Tryb pracy", None, "mdi:autorenew", None),
    "ZM_FAN1_SPE": ("Prędkość wentylatora #1", "RPM", "mdi:fan", "speed"),
    "ZM_FAN2_SPE": ("Prędkość wentylatora #2", "RPM", "mdi:fan", "speed"),
    "ZM_CUR_COMP_FREQ": ("Częstotliwość sprężarki", "Hz", "mdi:engine", "frequency"),
    "PWM_1": ("Pompa obiegu grzewczego", "%", "mdi:pump", "power"),
    
    # Status
    "SW_VERSION": ("Wersja oprogramowania", None, "mdi:chip", None),
    "CUN_HCU": ("Numer krzywej grzewczej", None, "mdi:chart-line", None),
    "CUN_D_HCU": ("Podbicie krzywej grzewczej", "°C", "mdi:thermometer", "temperature"),

    # Energy
    "ZM_AC_IN_VOL": ("Napięcie wejściowe", "V", "mdi:flash", "voltage"),
    "ZM_AC_IN_CUR": ("Prąd wejściowy", "A", "mdi:current-ac", "current"),
    "ZM_AC_IN_PWR": ("Aktualny pobór mocy", "W", "mdi:power", "power"),
    "ZM_AC_IN_ENERGY": ("Energia całkowita", "kWh", "mdi:counter", "energy")
}

NUMBERS_VARIABLES = { # Name, Unit, Icon, Min, Max, Step, Mode(0 - )
    "CUN_HCU": ("Numer krzywej grzewczej", None, "mdi:chart-line", 0, 9, 1, "AUTO"),
    "CUN_D_HCU": ("Podbicie krzywej grzewczej", "°C", "mdi:thermometer", 0, 10, 1, "AUTO")
#    "SX5": ("Temp. zadana CWU", "°C", "mdi:thermometer", 30, 55, 1, "BOX"),
#    "SX6": ("Temp. zadana CO", "°C", "mdi:thermometer", 10, 30, 1, "BOX"),
}


SELECTS_VARIABLES = { # Name, Unit, Icon, Options
    "MODE": ("Tryb pracy", None, "mdi:autorenew", ["AUTO", "ECO", "TIME", "AWAY", "OFF"])
}