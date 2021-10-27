import os
import logging
import requests as rq
from commons.Errors import ErrorType, Error
from datetime import datetime
from SubProcessInputOutputHandler import SubProcessInputOutputHandler
from commons.DataModels import ConnectorResult

VT_API_URL = 'https://www.virustotal.com/api/v3/domains/'
RELEVANT_STATUSES = ["harmless", "suspicious", "malicious"]
DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
TEXT_SUFF = ".txt"
DONE_SUFF = ".done"


# todo - handle exceptions, input validations and general validations (such as "if response.ok") in the different
#  functions

def retrieve_unprocessed_file_path(source_folder_path,
                                   logger):  # todo - exception from here should terminate connector's activity
    file_name_to_process = None
    error = None

    if os.path.isdir(source_folder_path):
        for file_name in os.listdir(source_folder_path):
            if not file_name.endswith(DONE_SUFF) and TEXT_SUFF in file_name:
                file_name_to_process = file_name
                break

        if file_name_to_process is None:
            error = Error(ErrorType.NO_FILES_TO_PROCESS, source_folder_path)
    else:
        error = Error(ErrorType.DIR_NOT_FOUND, source_folder_path)

    if error is not None:
        logger.warning(error.get_full_error_msg())
        raise Exception(error)

    return source_folder_path + "\\" + file_name_to_process # todo - check if there is more general way to do so - so it works on linux to


def get_entities_from_file(unprocessed_file_path, iteration_entities_count, logger):
    entities = []
    error = None

    if os.path.isfile(unprocessed_file_path):
        with open(unprocessed_file_path, 'r') as file:
            while iteration_entities_count > 0:
                line = file.readline()
                if not line:
                    break

                entities.append(line.strip())
                iteration_entities_count -= 1

        if len(entities) == 0:
            mark_file_as_done(unprocessed_file_path, logger)
            error = Error(ErrorType.EMPTY_FILE, unprocessed_file_path)
    else:
        error = Error(ErrorType.FILE_NOT_FOUND, unprocessed_file_path)

    if error is not None:
        logger.warning(error.get_full_error_msg())
        raise Exception(error)

    return entities


def get_date_from_utc(last_mod_date):
    return datetime.utcfromtimestamp(last_mod_date).strftime(DATE_FORMAT)


def analyze_entities(entities, api_key, logger):  # todo - add try/except
    alerts = dict()
    success = 0
    fails = 0
    for domain in entities:
        try:
            logger.debug(f"requesting information for domain {domain}")
            response = rq.get(f"{VT_API_URL}{domain}", headers={"x-apikey": api_key})
            vt_response_json = response.json()

            if response.ok:
                logger.debug(f"retrieved data successfully for domain {domain}")
                attr = vt_response_json.get("data").get("attributes")
                rep = attr.get("reputation")

                if rep <= 20:
                    last_analysis_stats = attr.get("last_analysis_stats")
                    total_votes = attr.get("total_votes")
                    last_mod_date = attr.get("last_modification_date")

                    if 0 <= rep:
                        harmless = last_analysis_stats.get("harmless")
                        suspicious = last_analysis_stats.get("suspicious")
                        malicious = last_analysis_stats.get("malicious")

                        if malicious > 0:
                            reason = "0 <= reputation <= 20 and domain flagged as malicious by one or more security vendors"
                        elif suspicious / (suspicious + harmless) > 0.05:
                            reason = "0 <= reputation <= 20 and domain flagged as suspicious by at least 5% of security vendors"
                        else:
                            alerts[domain] = {
                                "status": "Not Suspicious"
                            }
                            success += 1
                            continue

                    else:
                        reason = "rep < 0"

                    alerts[domain] = {
                        "status": "Suspicious",
                        "reasons": reason,
                        "reputation": rep,
                        "unweighted_total_votes": ', '.join([f'{value} community members voted this domain as {status}'
                                                             for status, value in total_votes.items()]),
                        "last_analysis_stats": ', '.join([f'{value} security vendors flagged this domain as {status}'
                                                          for status, value in last_analysis_stats.items()
                                                          if status in RELEVANT_STATUSES]),
                        "last_information_modification_date": get_date_from_utc(last_mod_date)
                    }
                else:
                    alerts[domain] = {
                        "status": "Not Suspicious"
                    }
                success += 1
            else:
                logger.debug(f"failed to retrieve data for domain {domain}")
                alerts[domain] = vt_response_json.get("error").get("message")
                fails += 1
        except Exception as e:
            logger.debug(f"failed to retrieve data for domain {domain}")
            alerts[domain] = str(e)
            fails += 1
    logger.info(f"successfully retrieved: {success} domains. "
                f"failed to retrieve: {fails} domains")
    return alerts


def mark_file_as_done(unprocessed_file_path, logger):
    new_name = unprocessed_file_path + DONE_SUFF
    os.rename(unprocessed_file_path, new_name)
    logger.debug(f"marked {unprocessed_file_path} as done")


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')

    io_mgr = SubProcessInputOutputHandler()
    connector_params = io_mgr.connector_params
    connector_result = ConnectorResult()

    logger = logging.getLogger(connector_params.connector_name)
    try:
        logger.info(f"Looking for file to process in {connector_params.source_folder_path}")
        unprocessed_file_path = retrieve_unprocessed_file_path(connector_params.source_folder_path, logger)
        logger.info(f"Starting to process file named {unprocessed_file_path}")
        entities = get_entities_from_file(unprocessed_file_path, connector_params.iteration_entities_count, logger)
        logger.info(
            f"Max entities to retrieve is {connector_params.iteration_entities_count}. "
            f"Retrieved {len(entities)} entities from file {unprocessed_file_path}")

        connector_result.alerts = analyze_entities(entities, connector_params.api_key, logger)
        # mark_file_as_done(unprocessed_file_path, logger)  # todo - keep uncommented

        io_mgr.end(connector_result)
    except Exception as e:
        io_mgr.end(e)


if __name__ == "__main__":
    main()
