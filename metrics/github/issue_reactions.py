from . import query


def fetch_reactions(client):
    print("getting reactions")
    # for reaction in query.reactions(client):
    # print(reaction)
    return query.reactions(client)
