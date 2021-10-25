
# # connector 1
# connector_settings_json1 = arr[0]
# connector_settings1 = DataModels.ConnectorSettings()
# _inhabit_connector_settings(connector_settings1, connector_settings_json1)
# # connector 2
# connector_settings_json2 = arr[1]
# connector_settings2 = DataModels.ConnectorSettings()
# _inhabit_connector_settings(connector_settings2, connector_settings_json2)

# ------ task 1
# proc = subprocess.Popen([sys.executable, connector_settings1.script_file_path], stdin=subprocess.PIPE,
#                         stdout=subprocess.PIPE)
# serialized = json.dumps(connector_settings1.params)
# # send the serialized data to proc's STDIN
# out, err = proc.communicate(serialized.encode())
# # time.sleep(connector_settings1.run_interval_seconds)
# ------
# ------ task 2
# if proc.returncode == 0: # proc will be in a queue
#     # save stdout to a file with timestamp
#     out_decoded = out.decode()
#     timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
#     path_to_write = f'{connector_settings1.output_folder_path}\\{timestamp}.json'
#
#     with open(path_to_write, 'w+', encoding='utf-8') as file:
#         json.dump(out_decoded, file, ensure_ascii=False, indent=4)
#     logging.info("Connector completed successfully")  # todo change msg to be more informative
# else:
#     logging.warning(f"Connector failed to sync results. "
#                     f"Reason: {out.decode()}")
# time.sleep(connector_settings1.run_interval_seconds) # will be the minimum between the sleep time of the connectors + 1
# --------
