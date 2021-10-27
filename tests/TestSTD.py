import json
from types import SimpleNamespace

import requests as rq
from Errors import ErrorType, Error

RELEVANT_STATUSES = ["malicious", "suspicious", "harmless"]


def _analyze_entities(entities, alerts):  # todo - complete this method
    for domain in entities:
        response = rq.get(f"https://www.virustotal.com/api/v3/domains/{domain}",
                          headers={"x-apikey": "4524af8cd44905528c20ca0c23f9a74dd640bcc10fdeeb3f60fbddea8561a7a1"})

        print(response)
        print(response.status_code)
        vt_response_json = response.json()
        print(vt_response_json.get("data"))
        vt_response_json = response.json()
        domain_name = vt_response_json.get("data").get("id")
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
                    alerts[domain_name] = {
                        "status": "Not Suspicious"
                    }
                    continue

            else:
                reason = "rep < 0"

            alerts[domain_name] = {
                "status": "Suspicious",
                "reasons": reason,
                "reputation": rep,
                "unweighted_total_votes": ', '.join([f'{value} community members voted this domain as {status}'
                                                     for status, value in total_votes.items()]),
                "last_analysis_stats": ', '.join([f'{value} security vendors flagged this domain as {status}'
                                                  for status, value in last_analysis_stats.items()
                                                  if status in RELEVANT_STATUSES]),
                "last_modification_date": last_mod_date
            }
        else:
            alerts[domain_name] = {
                "status": "Not Suspicious"
            }


if __name__ == "__main__":  # ensure the script is run directl
    # arg = input()  # get input from STDIN (Python 3.x)
    # data = json.loads(arg)  # parse the JSON from the first argument
    # print("First name: {}".format(data["user"]["first_name"]))  # print to STDOUT
    # print("Last name: {}".format(data["user"]["last_name"]))  # print to STDOUT

    # entities = ["msn.com"]  # "ynet.com", "chao-yue.net", "facebook.com"
    # alerts = {}
    # _analyze_entities(entities, alerts)
    # print(alerts["msn.com"])

    # arr = []
    # if arr:
    #     print("filled")
    # else:
    #     print("not")
    pass