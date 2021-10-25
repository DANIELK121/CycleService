import glob
import json
import os
import subprocess
import sys
import logging
import DataModels
from datetime import datetime

DATE_FORMAT = "D%Y-%m-%dT%H-%M-%S"


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


def get_last_sync_time(output_folder_path):
    list_of_files = glob.glob(f"{output_folder_path}\\*")  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    last_file_timestamp = latest_file.split('.')[0].split('-', 1)[1]
    return datetime.strptime(last_file_timestamp, DATE_FORMAT)


def is_empty(output_folder_path):
    if not os.listdir(output_folder_path):
        return True
    else:
        return False


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')

    # loading connectors' settings
    connectors_settings = open("config\\ConnectorsSettingsConfig.json", "r")
    arr = json.load(connectors_settings)
    working_connectors_queue = []

    # extracting configurations into DataModels.ConnectorSettings objects
    connector_settings_arr = [create_connector_settings_object(connector_settings_json) for connector_settings_json in
                              arr]

    # handling finished missions
    while True:
        for connector_settings in connector_settings_arr:
            # if dir is empty or last file in it time stamp is larger than now
            output_folder_path = connector_settings.output_folder_path
            if is_empty(output_folder_path) or (datetime.now() - get_last_sync_time(
                    output_folder_path)).total_seconds() >= connector_settings.run_interval_seconds:
                logging.info(f"start running {connector_settings.connector_name}")
                proc = subprocess.Popen([sys.executable, connector_settings.script_file_path], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, encoding='utf8')
                # writing params as a line to STDIN so the connector can read it as a line
                proc.stdin.write(f"{json.dumps(connector_settings.params)}\n")
                proc.stdin.flush()

                working_connectors_queue.append([connector_settings, proc])

        while len(working_connectors_queue) > 0:

            for working_connector in working_connectors_queue:
                connector_settings, proc = working_connector[0], working_connector[1]

                return_code = proc.poll()
                if return_code is not None:
                    logging.info(f"return code for {connector_settings.connector_name} is {return_code}")
                    # timestamp of retrieved data
                    timestamp = datetime.now().strftime(DATE_FORMAT)

                    out, err = proc.communicate()
                    if return_code == 0:
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
                            f"Reason: {out}")

                    working_connectors_queue.remove(working_connector)


if __name__ == "__main__":
    main()
