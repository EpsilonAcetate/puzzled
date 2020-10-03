import discord
import sqlite3
import datetime
import re
from classes import *

meta = open('meta.txt').read().split()
token = meta[0]
dbname = meta[1]
hintchannel_ID = int(meta[2])
client = discord.Client()

cc = '!' # command character


admin_commands = ['sudo', 'pause', 'unpause', 'register_team', 'add_hints']
auth_admins = []

async def send_help(team):
	helptext = open('helptext.txt').read()
	await team.channel.send(helptext)

async def send_puzzle(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()

	name = team.content[1].lower()
	if name in team.unlocked_puzzles: 
		c.execute('''SELECT link from puzzles where puzzle_name=?''', (name,))
		puzzlelink = c.fetchall()[0][0]
		await team.channel.send(name + ': ' + puzzlelink)
	else:
		await team.channel.send("that's not a valid puzzle, or you haven't unlocked it yet. !help for syntax")

async def process_guess(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()

	puzzle = team.content[1].lower()
	guess = team.content[2].lower()
	if puzzle in team.solved_puzzles:
		await team.channel.send("puzzle already solved")
	elif puzzle in team.unlocked_puzzles: 
		c.execute('''SELECT answer from puzzles where puzzle_name=?''', (puzzle,))
		answer = c.fetchall()[0][0]

		print(answer, guess)

		if answer == guess:
			await team.channel.send("yep! That's right!")
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'solve', team.name, team.now, puzzle, ''))
		else:
			await team.channel.send("sorry, wrong :(")
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'guess', team.name, team.now, puzzle, guess))
		conn.commit()
	else:
		await team.channel.send("that's not a valid puzzle, or you haven't unlocked it yet. !help for syntax")
	c.close()
	conn.close()

async def process_hint(team):
	hint_text = team.message.content 
	puzzle = team.content[1]
	hint_content = ' '.join(team.content[2:])

	if team.hints_remaining <= 0: 
		await team.channel.send('sorry, no hints remaining')
	elif puzzle in team.solved_puzzles:
		await team.channel.send("puzzle already solved")	
	elif puzzle in team.unlocked_puzzles:
		conn = sqlite3.connect(dbname)
		c = conn.cursor()

		request = 'team ' + team.name + ' is asking for a hint on ' + puzzle + ': ```' + hint_content + '``` link: ' + team.message.jump_url
		hint_channel = team.client.get_channel(hintchannel_ID)
		c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'hint', team.name, team.now, puzzle, hint_content))
		conn.commit()
		await team.channel.send('ok, a TA will pop in w hint soon')
		await hint_channel.send(request)
	else: 
		await team.channel.send("that's not a valid puzzle, or you haven't unlocked it yet. !help for syntax")		
	c.close()
	conn.close()


async def send_status(team):
	await team.channel.send("solved puzzles: "+ str(team.solved_puzzles) + "\nunsolved puzzles: "+str(team.unsolved_puzzles) + "\nhints remaining: " + str(team.hints_remaining) + "\nhints used: " + str(team.hints_used))

async def send_lb(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' SELECT team_name, count(*), MAX(timestamp) from events where type='solve' group by team_name order by MAX(timestamp)''')
	lb = c.fetchall()
	await team.channel.send(str(lb))

async def sudo(message, client): 
	query = re.findall('```(?P<ch>.*?)```', message.content)
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(query)
	c.close()


general_commands = {'help':send_help, 'goto': send_puzzle, 'guess':process_guess, 
					'hint':process_hint, 'status':send_status, 'leaderboard':send_lb}


def run_admin_command(message, client):
	pass

@client.event
async def on_message(message):
	if message.author != message.guild.me:
		if any([(cc+x) == message.content.split()[0] for x in admin_commands]):
			if str(message.author.id) in auth_admins:
				await run_admin_command(message, client)
			else:
				await message.add_reaction("😡")
		else:
			team = Team(message, client)
			for cmd in general_commands.keys():
				if cc+cmd in message.content:
					await general_commands[cmd](team)

@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

client.run(token)
