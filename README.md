# Cycle Service and VirusTotal API Connector – Docs
## Preface
The VirusTotalAPI Connector reads domains’ names from `.txt` files. For each domain it is querying the [VirusTotal API]((https://developers.virustotal.com/reference#overview)) and retrieves information about the domain. It then concludes whether the domain is suspicious, in a security manner, according to it’s VirusTotal `reputation` (“domain's score calculated from the votes of the VirusTotal's community”) and additional parameters in the response. Finally, it outputs the result to the process `STDOUT`.

The Cycle Service is a service with an infinite loop, that runs python subprocess of connector scripts at configured intervals. The connectors generate data, and the Cycle Service saves it to an output folder.

The framework is designed to accommodate different types of connectors (each with its own code) and run several instances of them with separate configuration.

In this document I will do a high-level overview of the project, go over important implementation details and How To Run instructions.
## How To Run
- Simply run `python CycleService.py` from the project folder (“Python Exercise”)

- Connectors’ configuration

	- The configuration file is under `./config/ConnectorsSettingsConfig.json` (“.” Indicates the project folder). 
	- Right now there are 2 connectors’ configurations there. Feel free to change existing configurations or add more configurations to activate more instances of the connector.
  
  NOTICE: for each connector’s configurations - `script_file_path`, `params`, `params.source_folder_path` and `params.api_key` are **MANDATORY** parameters, the connector wouldn’t be able to run without them.

## High Level Overview and Implementation Details
### Cycle Service
- First things first, importing configurations from the configuration file. It then maps each configuration object to a `ConnectorRunParams` object. Some conf. fields are optional and will be filled with default values if missing. Others are mandatory, as stated above.
- From here there are 2 main stages that happens one after the other in a loop – activating connectors and reading their results:
	- Activating connectors is done in predefined intervals. A connector won’t be activated until `(Now() – connector.last_sync_time) >= connector.run_interval`, or `connector.run_interval==None`. When activated, the connector is running in a subprocess. The service communicates with the subprocess via `PIPE`, so after initiating the subprocess I am using `Futures` to communicate asynchronously with the subprocess. This is crucial for connectors that generate large amount of data, so the `PIPE` won’t get filled when they write to it. Otherwise, it can cause a service-subprocess deadlock and the subprocess will never exit. After a connector is activated, its `ConnectorRunParams`, along with its subprocess and future objects, are inserted to a dictionary (`dict`) so the service can check for them again later.
	- Reading results – for each connector in `dict`, the service is checking its future and subprocess status. If they are done the service is trying to read the results from the future object. If the reading was successful then the service will write the results to a file or print an error message, according to the subprocess `return_code`.
### VirusTotal Connector
- On activation, tries to read `ConnectorParams` object from the subprocess `STDIN`. If some mandatory parameters are missing it alerts and exists.
- Searches in the given source directory for unprocessed `.txt` files to process. If a file is found and it is not empty, the connector will treat each line in it as a domain name.
- For each domain name the connector is querying the [VirusTotal API](https://developers.virustotal.com/reference#overview) and retrieves information about the domain. It then concludes whether the domain is suspicious, in a security manner, mainly according to its VirusTotal `reputation` (“domain's score calculated from the votes of the VirusTotal's community”). Special cases are when the absolute value of reputation is low (`-10≤reputation≤20`). Then decision is based on information from URL scanners and their insight about the domain (insights that were taken in account are `harmless`/`suspicious`/`malicious`) – one URL scanner flagging the domain as `malicious` or 5% URL scanners flagging as `suspicious` will indicate domain is `SUSPICIOUS` (otherwise `NOT_SUSPICIOUS`). This information is gathered in the API result under the `last_analysis_stats` attribute.
In such cases, I chose to base the decision on this attribute according to this note about `reputation` ([from TotalVirus Domains documentation](https://developers.virustotal.com/reference#domains-1)) ![About VirusTotal API reputation](/assets/images/img.png) Focusing the sentence: “The higher the absolute number, the more that you may trust a given score”. The difference between the upper and lower boundaries is because I want to be more cautious with low positive reputation domains – in my opinion, it is preferable to get a false SUSPICIOUS than a false NOT_SUSPICIOUS when talking about potentially malicious domains.
- Results are gathered and written to the subprocess `STDOUT`. Then the subprocess exits with a 0-value return code.
- When exceptions occur, or some input validation fails, the subprocess may exit with a 1-value return code. This indicates a problem that couldn’t be handled and results will not be written to a file.
### Additional Information
#### Logging
Each process has its own logger (all types are defined in `“Python Exercise”/commons/MyLogger.py`). The loggers are used to log important landmarks during the run and warn about special errors and exceptions. Each logger outputs log messages to the `STDERR` of its process.

#### Source Files
Under `“Python Exercise”/source_folders/`, each connector has a different source folder. Each contains various `.txt` files. In a file, each line is treated as a domain name, and each file may hold many domain names. Along with valid `.txt` files, I’ve put there empty `.txt` files and files with invalid domain names or empty lines, so it is possible to see how the service/connector handle these cases.

