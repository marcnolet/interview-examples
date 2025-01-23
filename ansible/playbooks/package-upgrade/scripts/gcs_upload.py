#!/usr/bin/env python3
"""
This script provides functionality to upload a local folder to Google Cloud Storage (GCS).

It includes functions to validate the GCS bucket, validate the local folder path,
and upload the folder contents to GCS using the gcloud CLI.

The script can be run as a standalone program with command-line arguments:
- folder_path: The local folder path to upload
- bucket_path: The Google Cloud Storage bucket path
- --debug: Optional flag to print commands instead of executing them

Usage:
    python gcs_upload.py <folder_path> <bucket_path> [--debug]

The script uses the gcloud command-line tool, so make sure it's installed and
configured with the appropriate Google Cloud project.
"""

import subprocess
import os
from typing import List


def validate_gcs_bucket(bucket_path: str, debug: bool = False) -> bool:
    """
    Validate if the specified Google Cloud Storage bucket exists.
    If the bucket doesn't exist, attempt to create it.

    Args:
        bucket_path (str): The Google Cloud Storage bucket path (e.g., 'gs://my-bucket').
        debug (bool): If True, print the command instead of executing it.

    Returns:
        bool: True if the bucket exists or was successfully created, False otherwise.

    Raises:
        subprocess.CalledProcessError: If the gcloud command fails.
    """
    gcloud_command: List[str] = [
        "gcloud",
        "storage",
        "ls",
        "-b",
        bucket_path,
    ]

    if debug:
        print(f"Debug: Bucket validation command: {' '.join(gcloud_command)}")
        return True

    try:
        subprocess.run(gcloud_command, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError:
        # Bucket doesn't exist, try to create it
        create_command: List[str] = [
            "gcloud",
            "storage",
            "buckets",
            "create",
            bucket_path,
        ]

        if debug:
            print(f"Debug: Bucket creation command: {' '.join(create_command)}")
            return True

        try:
            subprocess.run(create_command, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False


def validate_folder_path(folder_path: str) -> bool:
    """
    Validate if the specified folder path exists and is not empty.

    Args:
        folder_path (str): The local folder path to validate.

    Returns:
        bool: True if the folder exists and is not empty, False otherwise.
    """
    if not os.path.isdir(folder_path):
        return False

    return len(os.listdir(folder_path)) > 0


def upload_folder_to_gcs(bucket_path: str, folder_path: str, debug: bool = False) -> None:
    """
    Upload a folder and its contents to a Google Cloud Storage bucket using the gcloud CLI.

    Args:
        bucket_path (str): The Google Cloud Storage bucket path 
        (e.g., 'gs://my-bucket/path/to/destination').
        folder_path (str): The local folder path to upload.
        debug (bool): If True, print the commands instead of executing them.

    Raises:
        ValueError: If the bucket doesn't exist or the folder is invalid.
        subprocess.CalledProcessError: If the gcloud command fails.
    """
    if not validate_gcs_bucket(bucket_path.split("/")[0] + "//" + bucket_path.split("/")[2], debug):
        raise ValueError(f"The specified bucket does not exist: {bucket_path}")

    if not validate_folder_path(folder_path):
        raise ValueError(f"The specified folder path is invalid or empty: {folder_path}")

    gcloud_command: List[str] = [
        "gcloud",
        "storage",
        "cp",
        "-r",
        folder_path,
        bucket_path,
    ]

    if debug:
        print(f"Debug: Upload command: {' '.join(gcloud_command)}")
    else:
        try:
            subprocess.run(gcloud_command, check=True, capture_output=True, text=True)
            print(f"Successfully uploaded {folder_path} to {bucket_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error uploading folder to GCS: {e.stderr}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Upload a folder to Google Cloud Storage")
    parser.add_argument("folder_path", help="Local folder path to upload")
    parser.add_argument("bucket_path", help="Google Cloud Storage bucket path")
    parser.add_argument("--debug", action="store_true", help="Print commands instead of \
                        executing them")
    args = parser.parse_args()

    upload_folder_to_gcs(args.bucket_path, args.folder_path, args.debug)
