class ConnectorSettings(object):
    run_interval_seconds = None  # int - iterations interval in seconds for current connector
    script_file_path = None  # string - the file path to the connector script
    connector_name = None  # string - connector name
    params = None  # ConnectorParams object - see below
    output_folder_path = None  # string - file path for connector output


class ConnectorParams(object):
    source_folder_path = None  # string - file path for entity list files
    iteration_entities_count = None  # int - how many entities to process each interval (ignore the rest)
    api_key = None  # string - virus total api key


class ConnectorResult(object):
    alerts = None  # Dictionary {string, any} - connector output with data per entity. Key = Entity, value = entity data


class ProcessInfo(object):
    proc = None  # Finished process
    out = None  # Bytes wrote to process stdout
    err = None  # Bytes wrote to process stderr
