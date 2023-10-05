def extract_name_from_rawdata(message_rawdata):
    start_index = message_rawdata.find(":") + 1
    end_index = message_rawdata.find("!")
    if start_index == 0 or end_index == -1:
        return 'unknown_name - see message.raw_data for details'
    else:
        return message_rawdata[start_index:end_index]