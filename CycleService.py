import json
import os
import subprocess
import sys
from commons import DataModels
from datetime import datetime

from commons.MyLogger import CycleServiceLogger
from commons.Utils import get_param_or_default, SUCCESS, NO_RECOVER, ABORT

DATE_FORMAT = "D%m-%d-%YT%H-%M-%S"
SERVICE_NAME = "CycleService"
CONFIG_FILE_PATH = "config/ConnectorsSettingsConfig.json"


def create_connector_run_params(connector_settings_json, index, logger):
    connector_run_params = DataModels.ConnectorRunParams()
    connector_run_params.connector_settings = create_connector_settings_object(connector_settings_json, index, logger)
    return connector_run_params


def create_connector_settings_object(connector_settings_json, index, logger):
    connector_settings = DataModels.ConnectorSettings()

    connector_settings.connector_name = get_param_or_default("connector_name", connector_settings_json, str,
                                                             f"VTConnector{index + 1}")
    connector_settings.run_interval_seconds = get_param_or_default("run_interval_seconds", connector_settings_json, int,
                                                                   5)
    connector_settings.output_folder_path = get_param_or_default("output_folder_path", connector_settings_json, str,
                                                                 f"output_folders/{connector_settings.connector_name}_output")
    connector_settings.script_file_path = get_param_or_default("script_file_path", connector_settings_json, str, None)
    connector_settings.params = get_param_or_default("params", connector_settings_json, dict, None)

    if connector_settings.params is not None:
        connector_settings.params["connector_name"] = connector_settings.connector_name

    # if not (connector_settings.script_file_path and connector_settings.params):
    #     logger.warn_mandatory_params_missing(connector_settings.connector_name)
    return connector_settings


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
    logger = CycleServiceLogger(SERVICE_NAME)
    working_connectors_processes_queue = dict()

    # loading connectors' settings
    connectors_settings_config_file = open(CONFIG_FILE_PATH, "r")
    connectors_settings_json_arr = json.load(connectors_settings_config_file)

    # initialization of ConnectorRunParams with ConnectorSettings for each connector
    connector_run_params_arr = [create_connector_run_params(connector_settings_json, index, logger) for
                                index, connector_settings_json in enumerate(connectors_settings_json_arr)]

    while True:
        for connector_run_params in list(connector_run_params_arr):
            connector_settings = connector_run_params.connector_settings
            try:
                # if last_sync is None or
                # connector's run_interval_seconds has passed since last_sync - try to activate connector
                if connector_run_params not in working_connectors_processes_queue.keys() and \
                        (connector_run_params.last_sync is None or (datetime.now() - connector_run_params.last_sync).total_seconds() >= connector_settings.run_interval_seconds):
                    # check presence of mandatory params
                    if connector_settings.params and connector_settings.script_file_path:
                        output_folder_path = connector_settings.output_folder_path
                        # checks that output folder exists. creates the folder if not
                        validate_or_create_folder(output_folder_path)
                        if proc := run_subprocess(connector_settings.script_file_path):
                            logger.info_connector_activation(connector_settings.connector_name)
                            # writing params as a line to STDIN so the connector can read it as a line
                            proc.stdin.write(f"{json.dumps(connector_settings.params)}\n")
                            proc.stdin.flush()
                            # adding working process to queue
                            working_connectors_processes_queue[connector_run_params] = proc
                        else:
                            logger.warn_not_valid_file_path(connector_settings.script_file_path)
                    else:
                        connector_run_params.last_sync = datetime.now()
                        logger.warn_mandatory_params_missing(connector_settings.connector_name)
            except Exception as e:
                logger.warn_exception_when_checking("connector run params", connector_settings.connector_name, str(e))

        for connector_run_params in list(working_connectors_processes_queue.keys()):
            proc = working_connectors_processes_queue[connector_run_params]
            connector_settings = connector_run_params.connector_settings
            try:
                return_code = proc.poll()
                # checking if process finished
                if return_code is not None:
                    # timestamp of data syncing
                    timestamp = datetime.now()
                    timestamp_string = timestamp.strftime(DATE_FORMAT)
                    connector_run_params.last_sync = timestamp

                    out, err = proc.communicate()
                    # save results to a file named by timestamp and connector's name
                    path_to_write = f'{connector_settings.output_folder_path}/{connector_settings.connector_name}-{timestamp_string}.json'
                    if return_code == SUCCESS:
                        connector_output = json.loads(out)
                        logger.info_successful_completion(connector_settings.connector_name, path_to_write)
                    elif return_code == ABORT:
                        # something went wrong - no results. writing error msg to file
                        connector_output = f"Connector {connector_settings.connector_name} failed to retrieve results. " \
                                           f"Reason: {out}"
                    else:
                        # unknown error. writing error msg to file
                        connector_output = f"{connector_settings.connector_name} encountered unexpected error. " \
                                           f"Reason: {out}"

                    if return_code != SUCCESS: logger.general_warning(connector_output)
                    create_write_json_file(path_to_write, connector_output)
                    del working_connectors_processes_queue[connector_run_params]
            except Exception as e:
                logger.warn_exception_when_checking("subprocess", connector_settings.connector_name, str(e))


if __name__ == "__main__":
    main()

# todo delete
# elif return_code == NO_RECOVER:
#     # unrecoverable condition. removing connector settings from execution list
#     connector_output = f"{connector_settings.connector_name} encountered unrecoverable condition. " \
#                        f"Reason: {out}. " \
#                        f"removing {connector_settings.connector_name} settings from execution list"
#     # connector_run_params_arr.remove(connector_run_params)
