from enum import Enum


class ErrorType(Enum):
    LOCAL_ERROR = ""
    NO_FILES_TO_PROCESS = "no more files to process in directory "
    DIR_NOT_FOUND = "couldn't find directory "
    EMPTY_FILE = "no entities found in file "
    FILE_NOT_FOUND = "couldn't find file "
