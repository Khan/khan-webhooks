#!/usr/bin/env python
"""Export khan-webhook secrets to a secrets.py file.

This script reads in the secrets that are needed to deploy this service
(as defined in `secrets-config.json`), fetches them from keeper and outputs a
secrets.py file. It is meant to be run as part of the deploy process.

TODO(dhruv): Output an encrypted json blob instead of a python file, configure
khan-webhooks to fetch the key from KMS.
"""

import json
import subprocess
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

SECRET_CONFIG_PATH = os.path.join(ROOT, "secrets-config.json")
OUTPUT_PATH = os.path.join(ROOT, "secrets.py")


def _load_secrets_config():
    with open(SECRET_CONFIG_PATH) as config_file:
        return json.load(config_file)


def _keeper_secrets_by_uid():
    """Fetch all accessible keeper secrets, keyed by keeper uid"""
    keeper_config_path = os.path.expanduser("~/.keeper-config.json")

    args = [
        "keeper", "export", "--config", keeper_config_path,  "--format=json"]
    keeper_export = json.loads(subprocess.check_output(args))

    return {
        keeper_record["uid"]: keeper_record["password"]
        for keeper_record in keeper_export["records"]
    }


def _get_relevant_secrets():
    """Get secret values from keeper for secrets defined in secrets-config

    Returns: a dict of the form {'secret_name': 'secret_value'}, where
        secret_name is the name given in `secrets-config.json` and secret_value
        is the string password fetched from keeper.
    """
    secrets_config = _load_secrets_config()
    keeper_secrets_by_uid = _keeper_secrets_by_uid()

    relevant_secrets = {}
    for secret_name, secret_dict in secrets_config.items():
        keeper_uid = secret_dict["id"]
        secret_value = keeper_secrets_by_uid.get(keeper_uid)
        if not secret_value:
            raise RuntimeError(
                "Could not find secret '%s' (keeper uid: %s): "
                "do you have permission?" %
                (secret_name, keeper_uid))
        relevant_secrets[secret_name] = secret_value

    return relevant_secrets


def _output_secrets_file(secrets_by_name):
    """Output a python secrets.py file given a dict of secrets by name

    This function writes a file of the form:

    <secret_name> = "<secret_value>""
    <secret_2_name> = "<secret_2_value>""
    """
    with open(OUTPUT_PATH, "w") as f:
        for secret_name, secret_value in secrets_by_name.items():
            f.write("%s = '%s'\n" % (secret_name, secret_value))


def main():
    relevant_secrets = _get_relevant_secrets()
    _output_secrets_file(relevant_secrets)


if __name__ == "__main__":
    main()
