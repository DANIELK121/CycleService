import DataModels
from DataModels import ConnectorParams
import json
import sys


class SubProcessInputOutputHandler(object):

    @property
    def connector_params(self):
        result = ConnectorParams()

        try:
            # get input from STDIN
            arg = sys.stdin.readline()
            # parse the JSON from the first argument
            params = json.loads(arg)
            result.source_folder_path = params.get("source_folder_path")
            result.iteration_entities_count = params.get("iteration_entities_count")
            result.api_key = params.get("api_key")
            result.connector_name = params.get("connector_name")

            return result
        except Exception as e:
            self.end(f"Error in SubProcessInputOutputHandler::connector_params: {e}")

    def end(self, connector_result):
        if isinstance(connector_result, DataModels.ConnectorResult):
            output = json.dumps(connector_result.alerts)
            return_code = 0
        else:
            output = str(connector_result)
            return_code = 1
        # pass connector output as stdout
        sys.stdout.write(output)
        # end current process
        exit(return_code)
