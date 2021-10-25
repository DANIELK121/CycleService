from DataModels import ConnectorParams
import json
import sys

class SubProcessInputOutputHandler(object):

    @property
    def connector_params(self):
        result = ConnectorParams()

        # get input from STDIN
        arg = input()
        # parse the JSON from the first argument
        params = json.loads(arg)
        result.source_folder_path = params.get("source_folder_path")
        result.iteration_entities_count = params.get("iteration_entities_count")
        result.api_key = params.get("api_key")

        return result

    def end(self, connector_result):
        """ connector_result is of type ConnectorResult"""
        # pass connector result as stdout
        sys.stdout.write(json.dumps(connector_result.alerts))
        # end current process
        exit(0)

