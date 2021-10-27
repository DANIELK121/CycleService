import sys
from datetime import datetime
from SubProcessInputOutputHandler import SubProcessInputOutputHandler
from DataModels import ConnectorResult
import os
import logging
import requests as rq

VT_API_URL = 'https://www.virustotal.com/api/v3/domains/'
RELEVANT_STATUSES = ["harmless", "suspicious", "malicious"]
DATE_FORMAT = '%m-%d-%Y %H:%M:%S'
TEXT_SUFF = ".txt"
DONE_SUFF = ".done"


# todo - handle exceptions, input validations and general validations (such as "if response.ok") in the different
#  functions

def retrieve_unprocessed_file_path(source_folder_path): # todo - exception from here should terminate connector's activity
    file_name_to_process = None
    warn_msg = None

    if os.path.isdir(source_folder_path):
        for file_name in os.listdir(source_folder_path):
            if not file_name.endswith(DONE_SUFF) and TEXT_SUFF in file_name:
                file_name_to_process = file_name
                break

        if file_name_to_process is None:
            warn_msg = f"no more files to process in directory {source_folder_path}!"
    else:
        warn_msg = f"directory {source_folder_path} wasn't found!"

    if warn_msg is not None:
        logging.warning(warn_msg)
        raise Exception(warn_msg)

    return source_folder_path + "\\" + file_name_to_process


def get_entities_from_file(unprocessed_file_path, iteration_entities_count):
    entities = []
    warn_msg = None

    if os.path.isfile(unprocessed_file_path):
        with open(unprocessed_file_path, 'r') as file:
            while iteration_entities_count > 0:
                line = file.readline()
                if not line:
                    break

                entities.append(line.strip())
                iteration_entities_count -= 1

        if len(entities) == 0:
            mark_file_as_done(unprocessed_file_path)
            warn_msg = f"No entities found in file {unprocessed_file_path}!"
    else:
        warn_msg = f"file {unprocessed_file_path} wasn't found!"

    if warn_msg is not None:
        logging.warning(warn_msg)
        raise Exception(warn_msg)

    return entities


def get_date_from_utc(last_mod_date):
    return datetime.utcfromtimestamp(last_mod_date).strftime(DATE_FORMAT)


def analyze_entities(entities, api_key):  # todo - add try/except
    alerts = dict()
    for domain in entities:
        try:
            response = rq.get(f"{VT_API_URL}{domain}", headers={"x-apikey": api_key})
            vt_response_json = response.json()

            if response.ok:
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
            else:
                alerts[domain] = vt_response_json.get("error").get("message")
        except Exception as e:
            alerts[domain] = str(e)
    return alerts


def mark_file_as_done(unprocessed_file_path):
    suffix = '.done'
    new_name = unprocessed_file_path + suffix
    os.rename(unprocessed_file_path, new_name)


def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%H:%M:%S')

    try:
        io_mgr = SubProcessInputOutputHandler()
        connector_params = io_mgr.connector_params
        connector_result = ConnectorResult()

        logging.info(f"Looking for file to process in {connector_params.source_folder_path}")
        unprocessed_file_path = retrieve_unprocessed_file_path(connector_params.source_folder_path)
        logging.info(f"Starting to process file named {unprocessed_file_path}")
        entities = get_entities_from_file(unprocessed_file_path, connector_params.iteration_entities_count)
        logging.info(
            f"Max entities to retrieve is {connector_params.iteration_entities_count}. "
            f"Retrieved {len(entities)} entities from file {unprocessed_file_path}")

        connector_result.alerts = analyze_entities(entities, connector_params.api_key)
        # _mark_file_as_done(unprocessed_file_path)  # todo - keep uncommented

        io_mgr.end(connector_result)
    except Exception as e:
        sys.stdout.write(str(e))
        exit(1)


if __name__ == "__main__":
    main()
