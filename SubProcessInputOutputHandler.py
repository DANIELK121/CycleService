from commons import DataModels
from commons.DataModels import ConnectorParams
import json
import sys
from commons.Errors import ErrorType
from commons.Utils import get_param_or_default, SUCCESS, ABORT


class SubProcessInputOutputHandler(object):

    @property
    def connector_params(self):
        result = ConnectorParams()

        try:
            # get input from STDIN
            arg = sys.stdin.readline()
            # parse the JSON from the first argument
            params = json.loads(arg)

            result.source_folder_path = self.get_param_or_exit("source_folder_path", params, str)
            result.api_key = self.get_param_or_exit("api_key", params, str)
            result.iteration_entities_count = get_param_or_default("iteration_entities_count", params, int, 5)
            result.connector_name = get_param_or_default("connector_name", params, str, "VTConnectorDefaultName")

            return result
        except Exception as e:
            self.end(ErrorType.LOCAL_ERROR.get_full_err_msg(
                f"Error in SubProcessInputOutputHandler::connector_params: {e}"))

    def end(self, connector_result):
        try:
            if isinstance(connector_result, DataModels.ConnectorResult):
                output = json.dumps(connector_result.alerts)
                return_code = SUCCESS
            else:
                # connector_result is of type Exception
                # output, return_code = self.extract_exception(connector_result)
                output = str(connector_result)
                return_code = ABORT
            # pass connector output as stdout
            sys.stdout.write(output)
            # end current process
            exit(return_code)
        except Exception as e:
            sys.stdout.write(str(e))
            exit(ABORT)

    def get_param_or_exit(self, key, json_obj, expected_type):
        if key in json_obj.keys() and json_obj.get(key) and isinstance(
                json_obj.get(key), expected_type):
            return json_obj.get(key)
        else:
            self.end(ErrorType.MISSING_MANDATORY_PARAM.get_full_err_msg(key))
