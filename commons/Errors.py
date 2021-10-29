from enum import Enum


class ErrorType(Enum):
    LOCAL_ERROR = ""
    NO_FILES_TO_PROCESS = "no more files to process in source directory:"
    DIR_NOT_FOUND = "couldn't find source directory:"
    EMPTY_FILE = "no entities found in source file:"
    FILE_NOT_FOUND = "couldn't find source file:"
    MISSING_MANDATORY_PARAM = "missing connector mandatory param:"
    INVALID_ITERATION_ENTITIES_COUNT = "invalid iteration entities count:"

    def get_full_err_msg(self, additional_info):
        return f"{self.value} {additional_info}"

# todo - delete
# class Error(object):
#
#     def __init__(self, error_type, additional_info):
#         self.error_type = error_type
#         self.additional_info = additional_info
#
#     def get_full_error_msg(self):
#         return self.error_type.value + self.additional_info
