from slack_bolt import App


bennet_bot_id = "B03UJ58MALV"


def get_app(signing_secret, token):
    return App(token=token, signing_secret=signing_secret)


def iter_messages(app, channel_id):
    start = end = 0

    for page in app.client.conversations_history(
        channel=channel_id,
        include_all_metadata=True,
        latest=end,
        oldest=start,
    ):
        for message in page["messages"]:
            if "bot_id" in message and message["bot_id"] == bennet_bot_id:
                yield message
