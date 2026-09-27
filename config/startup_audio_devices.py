import os
import sys
import json
import argparse

import sounddevice as sd

# Add the root directory to sys.path
root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_directory not in sys.path:
    sys.path.insert(0, root_directory)

from my_modules.my_logging import create_logger

chatzilla_device_hostapi_name = "Windows WASAPI"

logger = create_logger(
    debug_level='INFO', 
    logger_name="logger_startup_audio"
)

def get_wasapi_microphones(output_filepath=None):
    """
    Retrieve a flat list of WASAPI devices that have microphone capabilities (max_input_channels > 0).
    Optionally save all WASAPI devices to a JSON file.

    Args:
        output_filepath (str, optional): Path to save all WASAPI devices as a JSON file.
    
    Returns:
        list[dict]: A list of dictionaries describing available WASAPI microphone devices.
    """
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        wasapi_index = next(
            (i for i, api in enumerate(hostapis) if api["name"] == chatzilla_device_hostapi_name),
            None
        )
    except Exception as e:
        logger.error(f"Error querying sound devices: {e}")
        return []

    if wasapi_index is None:
        logger.error(f"WASAPI Host API '{chatzilla_device_hostapi_name}' not found.")
        return []

    # Collect all WASAPI devices
    wasapi_devices = [
        {
            "index": idx,
            "name": device["name"],
            "hostapi": chatzilla_device_hostapi_name,
            "max_input_channels": device["max_input_channels"],
            "max_output_channels": device["max_output_channels"],
            "default_samplerate": device["default_samplerate"],
        }
        for idx, device in enumerate(devices) if device["hostapi"] == wasapi_index
    ]

    # Save all WASAPI devices to JSON if output_filepath is provided
    if output_filepath:
        try:
            with open(output_filepath, "w", encoding="utf-8") as json_file:
                json.dump(wasapi_devices, json_file, indent=4)
            logger.info(f"[get_wasapi_microphones] WASAPI devices saved to {output_filepath}")
        except Exception as e:
            logger.error(f"[get_wasapi_microphones] Failed to save WASAPI devices to JSON: {e}")

    # Filter for microphones
    microphones = [device for device in wasapi_devices if device["max_input_channels"] > 0]

    logger.debug(f"[get_wasapi_microphones] Discovered mic devices: {microphones}")
    return microphones

def _escape_batch_set_value(value):
    """
    Escape the selected device name for a Windows batch SET command.
    """
    return (
        value
        .replace("\r", "")
        .replace("\n", "")
        .replace("%", "%%")
        .replace("^", "^^")
        .replace('"', "'")
    )

def write_runtime_env_bat(output_filepath, key, value):
    """
    Write a temporary batch file that sets the selected device for the current launcher process.
    This is intentionally runtime-only and should be deleted by the caller after it is used.
    """
    output_dir = os.path.dirname(os.path.abspath(output_filepath))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    escaped_value = _escape_batch_set_value(value)
    with open(output_filepath, "w", encoding="utf-8") as bat_file:
        bat_file.write("@echo off\n")
        bat_file.write(f'set "{key}={escaped_value}"\n')

def ensure_audio_device_selected(device_env_var="CHATZILLA_MIC_DEVICE_NAME", runtime_env_bat=None):
    """
    Prompt for a WASAPI microphone selection on every startup.

    The selected device is not persisted to config/.env. When runtime_env_bat is provided,
    a temporary batch file is written so the launcher can set the device for this run only.

    Args:
        device_env_var (str): The environment variable key storing the microphone name.
        runtime_env_bat (str, optional): Path to write a temporary batch file with SET commands.
    """
    logger.info(f"[ensure_audio_device_selected] Prompting for '{device_env_var}'. Existing saved values are ignored.")

    output_filepath = r'.\data\botears\detected_wasapi_audio_devices.json'
    if not os.path.exists(os.path.dirname(output_filepath)):
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

    microphones = get_wasapi_microphones(output_filepath=output_filepath)
    if not microphones:
        logger.error("[ensure_audio_device_selected] No WASAPI microphone devices found. Exiting.")
        raise RuntimeError("No WASAPI microphone devices are available.")

    print("\nWASAPI Microphone Devices:")
    for i, mic in enumerate(microphones):
        print(f"[{i}] {mic['name']} (In={mic['max_input_channels']}, Out={mic['max_output_channels']})")

    try:
        user_index = int(input("\nEnter the number of the device you want to use: "))
        new_device = microphones[user_index]["name"]
    except (ValueError, IndexError) as e:
        logger.error(f"[ensure_audio_device_selected] Invalid selection: {e}")
        raise RuntimeError("Invalid audio device selection.")

    os.environ[device_env_var] = new_device
    if runtime_env_bat:
        write_runtime_env_bat(runtime_env_bat, device_env_var, new_device)
        logger.info(f"[ensure_audio_device_selected] Selected device '{new_device}' written for this run only.")
    else:
        logger.info(f"[ensure_audio_device_selected] Selected device '{new_device}' set for this process only.")

    return new_device

def parse_args():
    parser = argparse.ArgumentParser(description="Prompt for a WASAPI microphone device.")
    parser.add_argument(
        "--runtime-env-bat",
        help="Path to a temporary .bat file that will set the selected device for the launcher process.",
    )
    parser.add_argument(
        "--device-env-var",
        default="CHATZILLA_MIC_DEVICE_NAME",
        help="Environment variable name to set for the selected microphone device.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    try:
        ensure_audio_device_selected(
            device_env_var=args.device_env_var,
            runtime_env_bat=args.runtime_env_bat,
        )
        logger.info("[main] Startup audio device setup complete.")
    except RuntimeError as e:
        logger.error(f"[main] Audio setup failed: {e}")
        sys.exit(1)
