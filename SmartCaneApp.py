"""

    This code is written by Hafez K.Irshaid, and updated by Jia Guo
    Western Michigan University
    Veering Adjustment Project for blind pedestrian.
    Date: May 14, 2017

"""

import math
import serial
import time
import json

enable_log = False
tag_rank = 0
keep_reading_tags = True


# this method will print if the logging is enabled.
def log(message):
    if enable_log:
        print(message)


# This class contains some constants used in this code.
class Constants:
    INVENTORY_READ_COMMAND = bytearray([0x43, 0x03, 0x01])
    TAG_FRAME_LENGTH = 22

    LEFT_TAG = "LEFT_TAG"
    CENTER_TAG = "CENTER_TAG"
    RIGHT_TAG = "RIGHT_TAG"
    UNKNOWN_TAG = "UNKNOWN_TAG"

    ACTION_VEER_LEFT = "ACTION_VEER_LEFT"
    ACTION_VEER_RIGHT = "ACTION_VEER_RIGHT"
    ACTION_KEEP_GOING = "ACTION_KEEP_GOING"
    ACTION_UNKNOWN = "ACTION_UNKNOWN"

    TAGS_JSON_FILE_NAME = "tags.json"
    SERIAL_PORT_DEVICE_NAME = "/dev/ttyUSB0"
    SERIAL_PORT_BAUD_RATE = 115200

    # tags.json json array keys.
    LEFT_TAG_JSON_FILE_KEY = "left_tags"
    RIGHT_TAG_JSON_FILE_KEY = "right_tags"
    CENTER_TAG_JSON_FILE_KEY = "center_tags"

    NUMBER_OF_LEFT_TAGS_THRESHOLD = 5
    NUMBER_OF_RIGHT_TAGS_THRESHOLD = 5
    NUMBER_OF_CENTER_TAGS_THRESHOLD = 5

    SLEEP_TIME = 0.1

    def __init__(self):
        raise RuntimeError("Constants Class can't be instantiated")


# this class is responsible for reading tags.json and populate the lists and then it can classify
# the tag ID direction.
class VeeringAdjustmentClassifier:
    def __init__(self):

        self.list_of_left_tags = list()
        self.list_of_right_tags = list()
        self.list_of_center_tags = list()

        with open(Constants.TAGS_JSON_FILE_NAME) as data_file:
            tags_json = json.load(data_file)

        for i in tags_json[Constants.LEFT_TAG_JSON_FILE_KEY]:
            self.list_of_left_tags.append(str(i))
        for i in tags_json[Constants.RIGHT_TAG_JSON_FILE_KEY]:
            self.list_of_right_tags.append(str(i))
        for i in tags_json[Constants.CENTER_TAG_JSON_FILE_KEY]:
            self.list_of_center_tags.append(str(i))

    def classify_tag(self, tag):

        tag_location = None
        if tag in self.list_of_left_tags:
            tag_location = Constants.LEFT_TAG
        elif tag in self.list_of_right_tags:
            tag_location = Constants.RIGHT_TAG
        elif tag in self.list_of_center_tags:
            tag_location = Constants.CENTER_TAG
        else:
            tag_location = Constants.UNKNOWN_TAG

        return tag_location


# this variable is created globaly to be accessed anywhere in the code that needs to classify
# a tag ID.
classifier = VeeringAdjustmentClassifier()


class RFIDTag:
    def __init__(self, rfid_tag_hex):
        self.rfid_tag_hex = rfid_tag_hex
        self.rfid_tag_str = self.get_tag_hex_rep_as_str()
        self.rssi = self.calculate_rssi_value()
        self.counter = 1
        self.location = classifier.classify_tag(self.get_tag_hex_rep_as_str())
        global tag_rank
        self.rank = tag_rank

    # This function increases the counter for the current tag.
    def increase_counter(self):
        self.counter += 1

    # This function returns byte array of the hex format of the tag.
    def get_rfid_tag_in_hex(self):
        return self.rfid_tag_hex

    # This function returns string representation of the hex format of the tag.
    def get_tag_hex_rep_as_str(self):
        return self.get_rfid_tag_id()

    # This function calculates the RSSI value for the tag.
    def calculate_rssi_value(self):
        rssi_value_hex = self.rfid_tag_hex[3]
        q = (rssi_value_hex & 0xF0) >> 4
        i = (rssi_value_hex & 0x0F)
        high_rssi = i
        low_rssi = q
        if q > i:
            high_rssi = q
            low_rssi = i

        delta_rssi = high_rssi - low_rssi
        rssi_value = 2.0 * high_rssi + 10.0 * math.log10(1.0 + math.pow(10, -delta_rssi / 10.0))
        return float(rssi_value / 15.00) * 100.0

    # This function returns the string representation of the tag ID.
    def get_rfid_tag_id(self):
        rfid_tag = ""
        for i in range(10, 22):
            rfid_tag += str(hex(self.rfid_tag_hex[i]))
        return rfid_tag.replace("0x", "-")

    # This function returns tag id with its RSSI value.
    def __str__(self):
        global tag_rank
        return "Tag ID: " + self.rfid_tag_str + ", RSSI = " + str(self.rssi) + ", counter = " + str(self.counter) \
               + ", location = " + str(self.location) + " , rank = " + str(tag_rank)

    # This function compares this Tag with anther one based on Tag ID.
    def __eq__(self, other):
        return self.get_tag_hex_rep_as_str() == other.get_tag_hex_rep_as_str()


class RFIDReader:
    def __init__(self):
        self.list_of_tags = list()

        # init serial port
        self.serialPort = serial.Serial(port=Constants.SERIAL_PORT_DEVICE_NAME,
                                        baudrate=Constants.SERIAL_PORT_BAUD_RATE)
        self.serialPort.bytesize = serial.EIGHTBITS
        self.serialPort.parity = serial.PARITY_NONE
        self.serialPort.stopbits = serial.STOPBITS_ONE
        self.serialPort.timeout = None
        self.serialPort.flush()
        # Writing the commands through serial upon initiation
        self.serialPort.write(Constants.INVENTORY_READ_COMMAND)
        # Reading the command from the serial to activate rfid reader
        self.serialPort.read(2)
        # Allow 0.5 sec for the command to be read
        time.sleep(0.5)
        # Consume the rest 20 bytes
        self.serialPort.read(1)
        # flush the buffer
        self.serialPort.flush()


    def tag_lookup(self, tag_hex_str_to_find):
        tag = None

        if len(self.list_of_tags) == 0:
            return None

        for i in self.list_of_tags:
            if i.get_tag_hex_rep_as_str() == tag_hex_str_to_find:
                tag = i
                break

        return tag

    def find_tag_in_list(self, rfid_tag_to_find):
        found_tag = None
        for i in self.list_of_tags:
            if str(i.get_tag_hex_rep_as_str()) == str(rfid_tag_to_find.get_tag_hex_rep_as_str()):
                return i
        return found_tag

    def write_read_inventory_command(self):
        # Writing read command
        self.serialPort.flush()
        self.serialPort.write(Constants.INVENTORY_READ_COMMAND)
        self.serialPort.flush()

    def read_inventory(self):
        # Reading UART buffer
        number_of_bytes_in_buffer = self.serialPort.inWaiting()
        row_tags_hex = self.serialPort.read(number_of_bytes_in_buffer)
        row_tags_hex_byte_array = bytearray()
        row_tags_hex_byte_array.extend(row_tags_hex)
        return row_tags_hex_byte_array

    def get_list_of_surrounding_tags(self):

        list_of_tags = list()
        self.write_read_inventory_command()

        # Wait until the reader read the tags.
        time.sleep(Constants.SLEEP_TIME)
        row_tags_hex_byte_array = self.read_inventory()

        number_of_tags_found = len(row_tags_hex_byte_array) / Constants.TAG_FRAME_LENGTH
        bytes_counter = 0
        log("number_of_tags_found = " + str(number_of_tags_found))
        # Populate list_of_tags.
        if number_of_tags_found != 0:
            tag = bytearray()
            for i in row_tags_hex_byte_array:
                tag.append(i)
                bytes_counter += 1
                if bytes_counter % Constants.TAG_FRAME_LENGTH == 0:
                    bytes_counter = 0
                    list_of_tags.append(RFIDTag(tag))
                    tag = bytearray()

            tag = bytearray()
        return list_of_tags

    # this method is going to read the tags and update the list to either increase the counter
    # or create new tag.
    def read_tags(self):

        list_of_surrounding_tags = self.get_list_of_surrounding_tags()

        log("number of surrounding tags: " + str(len(list_of_surrounding_tags)))

        for surrounding_tag in list_of_surrounding_tags:

            # Check if the tag exists and if so increase the counter.
            tag = self.find_tag_in_list(surrounding_tag)
            if tag is None:
                self.list_of_tags.append(surrounding_tag)
            else:
                tag.increase_counter()

    def get_list_of_read_tags(self):
        return self.list_of_tags

    def flush_list_of_tags(self):
        self.list_of_tags = list()


# This class represents the decision table for the veering action.
class VeeringAdjustmentDecisionTable:
    def __init__(self):

        self.decision_table = [[0 for x in range(4)] for y in range(8)]
        self.decision_table[0][0] = 0
        self.decision_table[0][1] = 0
        self.decision_table[0][2] = 0
        self.decision_table[0][3] = Constants.ACTION_UNKNOWN

        self.decision_table[1][0] = 0
        self.decision_table[1][1] = 0
        self.decision_table[1][2] = 1
        self.decision_table[1][3] = Constants.ACTION_VEER_LEFT

        self.decision_table[2][0] = 0
        self.decision_table[2][1] = 1
        self.decision_table[2][2] = 0
        self.decision_table[2][3] = Constants.ACTION_KEEP_GOING

        self.decision_table[3][0] = 0
        self.decision_table[3][1] = 1
        self.decision_table[3][2] = 1
        self.decision_table[3][3] = Constants.ACTION_KEEP_GOING

        self.decision_table[4][0] = 1
        self.decision_table[4][1] = 0
        self.decision_table[4][2] = 0
        self.decision_table[4][3] = Constants.ACTION_VEER_RIGHT

        self.decision_table[5][0] = 1
        self.decision_table[5][1] = 0
        self.decision_table[5][2] = 1
        self.decision_table[5][3] = Constants.ACTION_KEEP_GOING

        self.decision_table[6][0] = 1
        self.decision_table[6][1] = 1
        self.decision_table[6][2] = 0
        self.decision_table[6][3] = Constants.ACTION_KEEP_GOING

        self.decision_table[7][0] = 1
        self.decision_table[7][1] = 1
        self.decision_table[7][2] = 1
        self.decision_table[7][3] = Constants.ACTION_KEEP_GOING

    # this method is going to determine the appropriate action to be performed by the
    # blind pedestrian based on the decision_table
    def get_action_from_decision_table(self, left, center, right):

        action = Constants.ACTION_UNKNOWN
        for i in range(len(self.decision_table)):
            if self.decision_table[i][0] == left and self.decision_table[i][1] == center \
                    and self.decision_table[i][2] == right:
                action = self.decision_table[i][3]
                break
        return action


# this Class is responsible for sending data over bluetooth to mobile device
class BluetoothCommuncation:
    def __init__(self, mobile_device_name):
        self.mobile_device_name = mobile_device_name

    def send_action_to_mobile(self, action):
        log("I'm sending action " + action + " to phone " + self.mobile_device_name)

    @staticmethod
    def stop_reading_tags(self):
        global keep_reading_tags
        keep_reading_tags = False


def main():
    reader = RFIDReader()
    decision_table = VeeringAdjustmentDecisionTable()
    bluetooth_communication = BluetoothCommuncation("phone_name")

    global keep_reading_tags

    # loop for ever and keep sending actions to phone until stop reading.
    while keep_reading_tags:

        log("reading tags 10 times")
        # read tags 30 times
        global tag_rank
        tag_rank = 0
        for i in range(10):
            tag_rank += tag_rank
            reader.read_tags()

        list_of_found_left_tags = list()
        list_of_found_right_tags = list()
        list_of_found_center_tags = list()

        # store each tag in its approprte list
        for i in reader.get_list_of_read_tags():

            log(i)
            if i.location == Constants.CENTER_TAG:
                list_of_found_center_tags.append(i)
            elif i.location == Constants.LEFT_TAG:
                list_of_found_left_tags.append(i)
            elif i.location == Constants.RIGHT_TAG:
                list_of_found_right_tags.append(i)

        left = 0
        right = 0
        center = 0

        # TODO make these appropriate
        if len(list_of_found_center_tags) != 0:
            center = 1
        if len(list_of_found_right_tags) != 0:
            right = 1
        if len(list_of_found_left_tags) != 0:
            left = 1

        log("left : " + str(left) + ", right : " + str(right) + ", center : " + str(center))

        # Calculate the appropriate action based on the read tags and the count.
        action_to_be_performed = decision_table.get_action_from_decision_table(left, center, right)

        print("action : " + str(action_to_be_performed))
        bluetooth_communication.send_action_to_mobile(action_to_be_performed)

        reader.flush_list_of_tags()
        return str(action_to_be_performed)

if __name__ == '__main__':
    main()
