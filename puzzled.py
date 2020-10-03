import discord
import sqlite3
import datetime
import re

token = open('token.txt').read()
client = discord.Client()

cc = '!' # command character

admin_commands = ['sudo', 'pause', 'unpause', 'register_team', 'add_hints']
general_commands = ['help', 'goto', 'guess', 'hint', 'status', 'leaderboard']

auth_admins = []

async def run_query(message, client):
	pass


@client.event
async def on_message(message):
	if any([(cc+x) in message.content for x in admin_commands]):
		if str(message.author.id) in auth_admins:
			await run_admin_command(message, client)
		else:
			await message.add_reaction("😡")
	elif any([(cc+x) in message.content for x in general_commands]):
		await run_query(message, client)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

client.run(token)
