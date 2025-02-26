# Streamlit doesn't work nicely with the app file living in a library, so we pull the app out into its
# own script. This needs to be at the top level of the codebase because Streamlit automatically adds
# this file's directory to PYTHONPATH, which allows us to import modules from our library.

if __name__ == "__main__":
    from metrics.streamlit import app

    app.display()
