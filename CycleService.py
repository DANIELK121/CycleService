import glob
import json
import os
import subprocess
import sys
import logging
from commons import DataModels
from datetime import datetime
from commons.Utils import get_param_or_default, SUCCESS, NO_RECOVER, ABORT

DATE_FORMAT = "D%m-%d-%YT%H-%M-%S"


def create_connector_settings_object(connector_settings_json, index, logger):
    connector_settings = DataModels.ConnectorSettings()

    connector_settings.connector_name = get_param_or_default("connector_name", connector_settings_json, str, f"VTConnector{index+1}")
    connector_settings.run_interval_seconds = get_param_or_default("run_interval_seconds", connector_settings_json, int, 5)
    connector_settings.output_folder_path = get_param_or_default("output_folder_path", connector_settings_json, str, f"output_folders\\{connector_settings.connector_name}_output")
    connector_settings.script_file_path = get_param_or_default("script_file_path", connector_settings_json, str, None)
    connector_settings.params = get_param_or_default("params", connector_settings_json, dict, None)

    if connector_settings.params is not None:
        connector_settings.params["connector_name"] = connector_settings.connector_name

    if not (connector_settings.script_file_path and connector_settings.params):
        logger.warning(f"{connector_settings.connector_name} doesn't have mandatory params! it won't be scheduled to run")
    return connector_settings


def get_last_sync_time(output_folder_path):
    list_of_files = glob.glob(f"{output_folder_path}\\*")
    # get latest written file in folder
    latest_file = max(list_of_files, key=os.path.getctime)
    # file name format: VTConnector2-D10-26-2021T14-35-40.json
    last_file_timestamp = latest_file.split('.')[0].split('-', 1)[1]
    return datetime.strptime(last_file_timestamp, DATE_FORMAT)


def is_dir_empty(output_folder_path):
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


def run_subprocess(script_file_path):
    proc = None
    if os.path.isfile(script_file_path):
        proc = subprocess.Popen([sys.executable, script_file_path],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, encoding='utf8')
    return proc

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # - %(name)s -
                        datefmt='%H:%M:%S')

    logger = logging.getLogger("CycleService")
    # loading connectors' settings
    connectors_settings = open("config\\ConnectorsSettingsConfig.json", "r")
    connectors_settings_json_arr = json.load(connectors_settings)
    working_connectors_queue = []

    # extracting configurations into DataModels.ConnectorSettings objects
    connector_settings_arr = [connector_settings for
                              index, connector_settings_json in enumerate(connectors_settings_json_arr)
                              if (connector_settings := create_connector_settings_object(connector_settings_json, index, logger)).script_file_path
                              and connector_settings.params]

    while True:
        for connector_settings in list(connector_settings_arr):
            try:
                output_folder_path = connector_settings.output_folder_path
                # checks that output folder exists. creates the named folder if it is not exist already
                validate_or_create_folder(output_folder_path)
                # if output dir is empty or
                # connector's run_interval_seconds has passed since last sync - activate connector
                if is_dir_empty(output_folder_path) or (datetime.now() - get_last_sync_time(
                        output_folder_path)).total_seconds() >= connector_settings.run_interval_seconds:
                    if proc := run_subprocess(connector_settings.script_file_path):
                        logger.info(f"activated {connector_settings.connector_name} successfully")
                        # writing params as a line to STDIN so the connector can read it as a line
                        proc.stdin.write(f"{json.dumps(connector_settings.params)}\n")
                        proc.stdin.flush()
                        # adding working process to queue
                        working_connectors_queue.append([connector_settings, proc])
                    else:
                        logger.warning(f"{connector_settings.script_file_path} is not a valid file path. "
                                       f"removing {connector_settings.connector_name} settings from execution list")
                        connector_settings_arr.remove(connector_settings)
            except Exception as e:
                logger.warning(
                    f"Exception occurred when checking connector settings of {connector_settings.connector_name}\n"
                    f"exception msg: {str(e)}")

        while len(working_connectors_queue) > 0:
            for working_connector in list(working_connectors_queue):
                connector_settings, proc = working_connector[0], working_connector[1]
                try:
                    return_code = proc.poll()
                    # checking if process finished
                    if return_code is not None:
                        # timestamp of data syncing
                        timestamp = datetime.now().strftime(DATE_FORMAT)
                        out, err = proc.communicate()
                        # save results to a file named by timestamp and connector's name
                        path_to_write = f'{connector_settings.output_folder_path}\\{connector_settings.connector_name}-{timestamp}.json'
                        if return_code == SUCCESS:
                            connector_output = json.loads(out)
                            logger.info(f"Connector {connector_settings.connector_name} completed successfully. "
                                         f"Results were wrote to {path_to_write}")
                        elif return_code == ABORT:
                            # something went wrong - no results. writing error msg to file
                            connector_output = f"Connector {connector_settings.connector_name} failed to retrieve results. " \
                                      f"Reason: {out}"
                            logger.warning(connector_output)
                        elif return_code == NO_RECOVER:
                            # unrecoverable condition. removing connector settings from execution list
                            connector_output = f"{connector_settings.connector_name} encountered an unrecoverable condition. " \
                                           f"Reason: {out}" \
                                           f"removing {connector_settings.connector_name} settings from execution list"
                            logger.warning(connector_output)
                            connector_settings_arr.remove(connector_settings)
                        else:
                            # unknown error
                            connector_output = f"{connector_settings.connector_name} encountered an unexpected error. " \
                                      f"Reason: {out}"
                            logger.warning(connector_output)

                        create_write_json_file(path_to_write, connector_output)
                        working_connectors_queue.remove(working_connector)
                except Exception as e:
                    logger.warning(
                        f"Exception occurred when was checking subprocess of {connector_settings.connector_name}\n"
                        f"exception msg: {str(e)}")


if __name__ == "__main__":
    main()
