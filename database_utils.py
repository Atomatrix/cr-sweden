import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import yaml

with open('./settings.yml', encoding="utf8") as file:
    settings = yaml.load(file, Loader=yaml.FullLoader)
    username = settings['mongodb']['username']
    password = settings['mongodb']['password']
    database_name = settings['mongodb']['database-name']

def db():
    uri = f'mongodb+srv://{username}:{password}@{database_name}.mongodb.net/?retryWrites=true&w=majority'
    client = AsyncIOMotorClient(uri)

    return client['clashroyale']

# !! # Test a ping on the server, make sure details are valid
async def ping_server():

    uri = f'mongodb+srv://{username}:{password}@{database_name}.mongodb.net/?retryWrites=true&w=majority'
    client = AsyncIOMotorClient(uri)

    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        return True
    except Exception as e:
        return e


# !! # Utilities to modify the database to add or remove accounts (link and unlink)
async def add_user(discordid, cr_tag):

    data = {'discord_id': int(discordid), 'cr_tag': cr_tag, 'dunce': False}
    return await db().users.insert_one(data)

async def remove_user(discordid):
    return await db().users.delete_one({'discord_id': {'$eq': int(discordid)}})



# !! # Utilities related to dunce functions
async def change_dunce(discordid, new_value=True):

    document = await db().users.find_one({'discord_id': int(discordid)})
    document['dunce'] = new_value

    return await db().users.replace_one({'discord_id': int(discordid)}, document)

async def dunce_status(discordid):
    document = await db().users.find_one({'discord_id': int(discordid)})
    return document['dunce']

async def all_dunce_users():
    # Retrieve all Discord IDs where "dunce" is true
    cursor = db().users.find({"dunce": True}, {"discord_id": 1, "_id": 0})

    discord_ids = []
    async for document in cursor:
        discord_ids.append(document["discord_id"])

    return discord_ids



# !! # Utilities related to all users
async def all_linked_users():
    cursor = db().users.find({}, {"_id": 0, "discord_id": 1})
    ids = [entry["discord_id"] async for entry in cursor]
    return ids

async def all_linked_tags():
    cursor = db().users.find({}, {"_id": 0, "cr_tag": 1})
    tags = [entry["cr_tag"] async for entry in cursor]
    return tags

async def total_linked():
    return await db().users.count_documents({})



# !! # Utilities for fetching a Discord ID or tag from the database
async def get_tag(discordid):
    document = await db().users.find_one({'discord_id': int(discordid)})
    return document['cr_tag']

async def get_discordid(cr_tag):
    document = await db().users.find_one({'cr_tag': cr_tag})
    return document['discord_id']



# !! # Utilities for checking if an account is linked
async def is_linked_discord(discordid):
    document = await db().users.find_one({'discord_id': int(discordid)})
    if document is not None:
        return True
    else:
        return False

async def is_linked_cr(cr_tag):
    document = await db().users.find_one({'cr_tag': cr_tag})
    if document is not None:
        return True
    else:
        return False
