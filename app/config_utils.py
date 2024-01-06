import streamlit as st
import json

# Get config data from keyword arguments
def get_config_data(current_config):
    return json.dumps(current_config, indent=2)

# Get config data from keyword arguments
def get_config(config_keys, **kwargs):
    # For each key in config_keys set the corresponding keyword argument (e.g. id_columns)
    current_config = {key: kwargs[key] for key in config_keys}
    return current_config

def load_config(file_path):
    """Load configuration from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return None

def apply_config(config):
    """Apply a configuration to the Streamlit UI elements."""
    if config:
        # Assuming all your Streamlit widgets have keys set
        for key, value in config.items():
            # If item is a dictionary then pull the dictionary keys to a list for multiselect
            if isinstance(value, dict):
                values = value.values()
                keys = list(value.keys())
                # For each name in values set the corresponding session key (e.g. f"id_columns-key_0")
                for i, name in enumerate(values):
                    st.session_state[f"{key}-name_{keys[i]}"] = name
                # Convert keys to numeric and assign to value
                value = [int(key) for key in keys]
            st.session_state[key] = value

def save_config(config, path):
    """Save the configuration to the specified path."""
    try:
        with open(path, 'w') as file:
            json.dump(config, file)
        return True
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return False

