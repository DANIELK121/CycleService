import glob
import json
import os
import subprocess
import sys
import logging
import DataModels
from datetime import datetime

DATE_FORMAT = "D%m-%d-%YT%H-%M-%S"


# todo - handle exceptions, input validations and general validations (such as "if response.ok") in the different
#  functions

# todo - add input validation as Dvir said. give default values for some, if value is not there
def create_connector_settings_object(connector_settings_json):
    connector_settings = DataModels.ConnectorSettings()
    connector_settings.connector_name = connector_settings_json.get("connector_name")
    connector_settings.params = connector_settings_json.get("params")
    connector_settings.run_interval_seconds = connector_settings_json.get("run_interval_seconds")
    connector_settings.script_file_path = connector_settings_json.get("script_file_path")
    connector_settings.output_folder_path = connector_settings_json.get("output_folder_path")
    return connector_settings


def get_last_sync_time(output_folder_path):
    list_of_files = glob.glob(f"{output_folder_path}\\*")
    # get latest written file in folder
    latest_file = max(list_of_files, key=os.path.getctime)
    # file name format: VTConnector2-D10-26-2021T14-35-40.json
    last_file_timestamp = latest_file.split('.')[0].split('-', 1)[1]
    return datetime.strptime(last_file_timestamp, DATE_FORMAT)


def is_empty(output_folder_path):
    if os.listdir(output_folder_path):
        return False
    else:
        return True


def validate_or_create_folder(output_folder_path):
    if not os.path.isdir(output_folder_path):
        os.mkdir(output_folder_path)


def create_write_json_file(path_to_write, data):
    with open(path_to_write, 'w') as file:
        json.dump(data, file, indent=4)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',  # - %(name)s -
                        datefmt='%H:%M:%S')

    # loading connectors' settings
    connectors_settings = open("config\\ConnectorsSettingsConfig.json", "r")
    connectors_settings_json_arr = json.load(connectors_settings)
    working_connectors_queue = []

    # extracting configurations into DataModels.ConnectorSettings objects
    # todo - input validation in create_connector_settings_object() - check that key exists and its value
    connector_settings_arr = [create_connector_settings_object(connector_settings_json) for connector_settings_json in
                              connectors_settings_json_arr]

    # handling finished missions
    while True:
        for connector_settings in list(connector_settings_arr):
            try:
                output_folder_path = connector_settings.output_folder_path
                # checks that output folder exists. creates the named folder if it is not exist already
                validate_or_create_folder(output_folder_path)
                # if output dir is empty or
                # connector's run_interval_seconds has passed since last sync - activate connector
                if is_empty(output_folder_path) or (datetime.now() - get_last_sync_time(
                        output_folder_path)).total_seconds() >= connector_settings.run_interval_seconds:
                    logging.info(f"activating {connector_settings.connector_name}")
                    proc = subprocess.Popen([sys.executable, connector_settings.script_file_path],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE, encoding='utf8')
                    # writing params as a line to STDIN so the connector can read it as a line
                    proc.stdin.write(f"{json.dumps(connector_settings.params)}\n")
                    proc.stdin.flush()
                    # adding working process to queue
                    working_connectors_queue.append([connector_settings, proc])
            except Exception as e:   # todo - handle correctly
                if e is isinstance(dir_not_found_error):
                    logging.info(f"issue with {connector_settings.connector_name}'s source directory: {e}\n"
                                 f"connector won't be activated again until it's configuration is changed")
                    connector_settings_arr.remove(connector_settings)
                pass

        while len(working_connectors_queue) > 0:
            for working_connector in list(working_connectors_queue):
                try:
                    connector_settings, proc = working_connector[0], working_connector[1]

                    return_code = proc.poll()
                    # checking if process finished
                    if return_code is not None:
                        logging.info(f"{connector_settings.connector_name} finished with return code {return_code}")

                        # timestamp of syncing data
                        timestamp = datetime.now().strftime(DATE_FORMAT)
                        out, err = proc.communicate()
                        # save results to a file named by timestamp and connector's name
                        path_to_write = f'{connector_settings.output_folder_path}\\{connector_settings.connector_name}-{timestamp}.json'
                        if return_code == 0:
                            create_write_json_file(path_to_write, json.loads(out))
                            logging.info(f"Connector {connector_settings.connector_name} completed successfully. "
                                         f"Results were wrote to {path_to_write}")
                        else:
                            # something went wrong - no results. writing error msg to file
                            err_msg = f"Connector {connector_settings.connector_name} failed to retrieve results. " \
                                      f"Reason: {out}"
                            create_write_json_file(path_to_write, err_msg)
                            logging.warning(err_msg)

                        working_connectors_queue.remove(working_connector)
                except Exception as e:
                    pass  # todo - handle correctly


if __name__ == "__main__":
    main()
