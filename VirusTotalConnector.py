import os
import requests as rq

from commons.Errors import ErrorType
from datetime import datetime
from SubProcessInputOutputHandler import SubProcessInputOutputHandler
from commons.DataModels import ConnectorResult
from commons.MyLogger import VirusTotalConnectorLogger

VT_API_URL = 'https://www.virustotal.com/api/v3/domains/'
RELEVANT_STATUSES = ["harmless", "suspicious", "malicious"]
DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
TEXT_SUFF = ".txt"
DONE_SUFF = ".done"


# todo - handle exceptions, input validations and general validations (such as "if response.ok") in the different
#  functions

def retrieve_unprocessed_file_path(source_folder_path,
                                   logger):
    file_name_to_process = None
    error = None

    if os.path.isdir(source_folder_path):
        for file_name in os.listdir(source_folder_path):
            if not file_name.endswith(DONE_SUFF) and TEXT_SUFF in file_name:
                file_name_to_process = file_name
                break

        if file_name_to_process is None:
            error = ErrorType.NO_FILES_TO_PROCESS.get_full_err_msg(source_folder_path)
    else:
        error = ErrorType.DIR_NOT_FOUND.get_full_err_msg(source_folder_path)

    if error is not None:
        logger.general_warning(error)
        raise Exception(error)

    return f"{source_folder_path}/{file_name_to_process}"


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
            error = ErrorType.EMPTY_FILE.get_full_err_msg(unprocessed_file_path)
    else:
        error = ErrorType.FILE_NOT_FOUND.get_full_err_msg(unprocessed_file_path)

    if error is not None:
        logger.general_warning(error)
        raise Exception(error)

    return entities


def get_date_from_utc(last_mod_date):
    return datetime.utcfromtimestamp(last_mod_date).strftime(DATE_FORMAT)


def analyze_entities(entities, api_key, logger):
    alerts = dict()
    success = 0
    fails = 0
    for domain in entities:
        try:
            logger.debug_request_domain_info(domain)
            response = rq.get(f"{VT_API_URL}{domain}", headers={"x-apikey": api_key})
            vt_response_json = response.json()

            if response.ok:
                logger.debug_retrieved_successfully_from_domain(domain)
                attr = vt_response_json.get("data").get("attributes")
                rep = attr.get("reputation")

                if rep <= 20:
                    last_analysis_stats = attr.get("last_analysis_stats")
                    total_votes = attr.get("total_votes")
                    last_mod_date = attr.get("last_modification_date")

                    if -10 <= rep:
                        harmless = last_analysis_stats.get("harmless")
                        suspicious = last_analysis_stats.get("suspicious")
                        malicious = last_analysis_stats.get("malicious")

                        if malicious > 0:
                            reason = "Absolute value of reputation is low, but domain flagged as malicious by one or more security vendors"
                        elif suspicious / (suspicious + harmless) > 0.05:
                            reason = "Absolute value of reputation is low, but domain flagged as suspicious by at least 5% of security vendors"
                        else:
                            alerts[domain] = {
                                "status": "Not Suspicious"
                            }
                            success += 1
                            continue

                    else:
                        reason = "High negative reputation"

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
                logger.debug_retrieve_domain_info_failed(domain)
                alerts[domain] = vt_response_json.get("error").get("message")
                fails += 1
        except Exception as e:
            logger.debug_retrieve_domain_info_failed(domain)
            alerts[domain] = str(e)
            fails += 1
    logger.info_retrieve_results(success, fails)
    return alerts


def mark_file_as_done(unprocessed_file_path, logger: VirusTotalConnectorLogger):
    new_name = unprocessed_file_path + DONE_SUFF
    os.rename(unprocessed_file_path, new_name)
    logger.debug_marked_file_done(unprocessed_file_path)


def main():

    io_mgr = SubProcessInputOutputHandler()
    connector_params = io_mgr.connector_params
    connector_result = ConnectorResult()

    logger = VirusTotalConnectorLogger(connector_params.connector_name)
    try:
        logger.info_looking_file_in_folder(connector_params.source_folder_path)
        unprocessed_file_path = retrieve_unprocessed_file_path(connector_params.source_folder_path, logger)
        logger.info_file_processing(unprocessed_file_path)
        entities = get_entities_from_file(unprocessed_file_path, connector_params.iteration_entities_count, logger)
        logger.info_num_of_retrieved_entities_from_file(len(entities), unprocessed_file_path)

        connector_result.alerts = analyze_entities(entities, connector_params.api_key, logger)
        # mark_file_as_done(unprocessed_file_path, logger)  # todo - keep uncommented

        io_mgr.end(connector_result)
    except Exception as e:
        io_mgr.end(e)


if __name__ == "__main__":
    main()
