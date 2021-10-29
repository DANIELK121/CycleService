import logging


class MyLogger(object):

    def __init__(self, name, logging_lvl=logging.INFO):
        # initialization from https://docs.python.org/3/howto/logging.html#configuring-logging
        # create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging_lvl)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging_lvl)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        self.logger.addHandler(ch)

    def general_warning(self, warning_msg):
        self.logger.warning(warning_msg)


class CycleServiceLogger(MyLogger):

    def __init__(self, name, logging_lvl=logging.INFO):
        super().__init__(name, logging_lvl)

    def warn_mandatory_params_missing(self, connector_name):
        self.logger.warning(
            f"mandatory params (connector params/script file path) for {connector_name} are missing! it can't be scheduled to run")

    def info_connector_activation(self, connector_name):
        self.logger.info(f"activated {connector_name} successfully")

    def warn_not_valid_file_path(self, connector_name, file_path):
        self.logger.warning(f"can't start {connector_name}, {file_path} is not a valid file path")

    def warn_exception_when_checking(self, checking, connector_name, exc_msg):
        self.logger.warning(
            f"Exception occurred when checking {checking} of {connector_name}\n"
            f"exception msg: {exc_msg}")

    def info_successful_completion(self, connector_name, path_to_write):
        self.logger.info(f"Connector {connector_name} completed successfully. "
                         f"Results were wrote to {path_to_write}")


class VirusTotalConnectorLogger(MyLogger):

    def __init__(self, name, logging_lvl=logging.INFO):
        super().__init__(name, logging_lvl)

    def info_looking_file_in_folder(self, folder_path):
        self.logger.info(f"Looking for file to process in {folder_path}")

    def info_file_processing(self, file_path):
        self.logger.info(f"Starting to process file named {file_path}")

    def info_num_of_retrieved_entities_from_file(self, num_of_entities, file_path):
        self.logger.info(
            f"Retrieved {num_of_entities} entities from file {file_path}")

    def info_retrieve_results(self, success, fails):
        self.logger.info(f"successfully retrieved info for: {success} domain(s). "
                         f"failed to retrieve info for: {fails} domain(s)")

    def debug_request_domain_info(self, domain):
        self.logger.debug(f"requesting information for domain {domain}")

    def debug_retrieved_successfully_from_domain(self, domain):
        self.logger.debug(f"retrieved data successfully for domain {domain}")

    def debug_retrieve_domain_info_failed(self, domain):
        self.logger.debug(f"failed to retrieve data for domain {domain}")

    def debug_marked_file_done(self, unprocessed_file_path):
        self.logger.debug(f"marked {unprocessed_file_path} as done")
