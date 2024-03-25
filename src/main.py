"""Module imports"""

import logging
import json
import time
import os
from signalrcore.hub_connection_builder import HubConnectionBuilder
from dotenv import load_dotenv
import requests
import psycopg2


class App:
    """Class representing the application"""
    '''Adding some comments for testing purposes'''

    load_dotenv()

    def __init__(self):
        self._hub_connection = None
        self.ticks = 10

        # To be configured
        self.env_var_host = os.getenv("HOST")  # Setup your host here
        self.env_var_token = os.getenv("TOKEN")  # Setup your token here
        self.env_var_t_max = os.getenv("T_MAX")  # Setup your max temperature here
        self.env_var_t_min = os.getenv("T_MIN")  # Setup your min temperature here
        self.env_var_database_url = os.getenv("DATABASE_URL")

    def __del__(self):
        if self._hub_connection is not None:
            self._hub_connection.stop()

    def start(self):
        """Start Oxygen CS."""
        self.setup_sensor_hub()
        self._hub_connection.start()
        print("Press CTRL+C to exit.")
        while True:
            time.sleep(2)

    def setup_sensor_hub(self):
        """Configure hub connection and subscribe to sensor data events."""
        self._hub_connection = (
            HubConnectionBuilder()
            .with_url(f"{self.env_var_host}/SensorHub?token={self.env_var_token}")
            .configure_logging(logging.INFO)
            .with_automatic_reconnect(
                {
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 999,
                }
            )
            .build()
        )
        self._hub_connection.on("ReceiveSensorData", self.on_sensor_data_received)
        self._hub_connection.on_open(lambda: print("||| Connection opened."))
        self._hub_connection.on_close(lambda: print("||| Connection closed."))
        self._hub_connection.on_error(
            lambda data: print(f"||| An exception was thrown closed: {data.error}")
        )

    def on_sensor_data_received(self, data):
        """Callback method to handle sensor data on reception."""
        try:
            print(data[0]["date"] + " --> " + data[0]["data"], flush=True)
            timestamp = data[0]["date"]
            temperature = float(data[0]["data"])
            action = self.take_action(temperature)
            self.save_event_to_database(timestamp, temperature, action)
        except (IndexError, ValueError) as err:
            print(err)

    def take_action(self, temperature):
        """Take action to HVAC depending on current temperature."""
        if float(temperature) >= float(self.env_var_t_max):
            self.send_action_to_hvac("TurnOnAc")
            return "TurnOnAc"
        if float(temperature) <= float(self.env_var_t_min):
            self.send_action_to_hvac("TurnOnHeater")
            return "TurnOnHeater"
        return None

    def send_action_to_hvac(self, action):
        """Send action query to the HVAC service."""
        r = requests.get(
            f"{self.env_var_host}/api/hvac/{self.env_var_token}/{action}/{self.ticks}",
            timeout=10,
        )
        details = json.loads(r.text)
        print(details, flush=True)

    def save_event_to_database(self, timestamp, temperature, action):
        """Save sensor data into database."""
        try:
            conn = psycopg2.connect(self.env_var_database_url)
            cur = conn.cursor()
            cur.execute(
                'INSERT INTO "OxygenCS_SensorData" '
                '("timestamp", "temperature", "action") '
                "VALUES (%s, %s, %s)",
                (timestamp, temperature, str(action)),
            )

            conn.commit()
            print("Data saved successfully")
        except psycopg2.Error as e:
            print(f"Failed to save event to database: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


if __name__ == "__main__":
    app = App()
    app.start()
