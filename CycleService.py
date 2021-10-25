import json
import subprocess
import sys
import logging
import threading
import time

import DataModels
from datetime import datetime

lock = threading.Lock()


# todo - handle exceptions, input validations and general validations (such as "if response.ok") in the different
#  functions

def create_connector_settings_object(connector_settings_json):
    connector_settings = DataModels.ConnectorSettings()
    connector_settings.connector_name = connector_settings_json.get("connector_name")
    connector_settings.params = connector_settings_json.get("params")
    connector_settings.run_interval_seconds = connector_settings_json.get("run_interval_seconds")
    connector_settings.script_file_path = connector_settings_json.get("script_file_path")
    connector_settings.output_folder_path = connector_settings_json.get("output_folder_path")
    return connector_settings


def run_connector(connector_settings, finished_missions_queue):
    process_info = DataModels.ProcessInfo()
    proc = subprocess.Popen([sys.executable, connector_settings.script_file_path], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)
    serialized = json.dumps(connector_settings.params)
    # send the serialized data to proc's STDIN
    process_info.out, process_info.err = proc.communicate(serialized.encode())
    process_info.proc = proc

    # timestamp of retrieved data
    timestamp = datetime.now().strftime("D%Y-%m-%dT%H-%M-%S")
    with lock:
        finished_missions_queue.append(
            [process_info, connector_settings, timestamp])  # adding finished mission details to queue
    threading.Timer(connector_settings.run_interval_seconds, run_connector, args=(connector_settings,
                                                                                  finished_missions_queue)).start()


def handle_results(finished_missions_queue):
    while len(finished_missions_queue) > 0:
        with lock:
            mission_details = finished_missions_queue.pop()

        process_info = mission_details[0]
        connector_settings = mission_details[1]
        timestamp = mission_details[2]

        out = process_info.out
        if process_info.proc.returncode == 0:
            # save results to a file named with connector's name and timestamp
            path_to_write = f'{connector_settings.output_folder_path}\\{connector_settings.connector_name}-{timestamp}.json'
            with open(path_to_write, 'w') as file:
                json.dump(json.loads(out), file, indent=4)

            logging.info(f"Connector {connector_settings.connector_name} completed successfully. "
                         f"Results were wrote to {path_to_write}")  # todo change msg to be more informative - add connector name and where it wrote to
        else:
            # something went wrong - no results. todo - writing error to file
            logging.warning(
                f"Connector {connector_settings.connector_name} failed to sync results. "  # todo change msg to be more informative - add connector name
                f"Reason: {out.decode()}")


def main():
    # loading connectors' settings
    connectors_settings = open("config\\ConnectorsSettingsConfig.json", "r")
    arr = json.load(connectors_settings)
    finished_missions_queue = []

    # extracting configurations into DataModels.ConnectorSettings objects
    connector_settings_arr = [create_connector_settings_object(connector_settings_json) for connector_settings_json in arr]

    # initializing connectors' and files writer work
    for connector_settings in connector_settings_arr:
        threading.Thread(target=run_connector, args=(connector_settings, finished_missions_queue)).start()

    # handling finished missions
    while True:
        # todo - will run every 30 seconds for now. in future may run every: the minimum between the sleep time of the
        #  connectors + 1
        time.sleep(10)
        handle_results(finished_missions_queue)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(message)s',
                        datefmt='%H:%M:%S')
    main()
