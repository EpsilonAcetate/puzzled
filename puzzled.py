import discord
import sqlite3
import datetime
import re
from classes import *

meta = open('meta.txt').read().split()
token = meta[0]
dbname = meta[1]
hintchannel_ID = int(meta[2])
admin_IDs = meta[3]

client = discord.Client()

cc = '!' # command character

auth_admins = [int(x) for x in admin_IDs.split(',')]

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
			conn.commit()
			c.execute(''' SELECT puzzle_name from puzzles where unlocked_at=? ''', (len(team.solved_puzzles)+1,))
			unlocked_puzzles = [x[0] for x in c.fetchall()]
			for p in unlocked_puzzles:
				c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'unlock', team.name, team.now, p, ''))
				await team.channel.send('puzzle unlocked: '+p)
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
		c.close()
		conn.close()

	else: 
		await team.channel.send("that's not a valid puzzle, or you haven't unlocked it yet. !help for syntax")		


async def send_status(team):
	await team.channel.send("solved puzzles: "+ str(team.solved_puzzles) + "\nunsolved puzzles: "+str(team.unsolved_puzzles) + "\nhints remaining: " + str(team.hints_remaining) + "\nhints used: " + str(team.hints_used))

async def send_lb(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' SELECT team_name, count(*), MAX(timestamp) from events where type='solve' group by team_name order by count(*) desc, MAX(timestamp)''')
	lb = c.fetchall()
	await team.channel.send(str(lb))

async def sudo(message, client): 
	query = re.findall('```(?P<ch>.*?)```', message.content)[0]
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(query)
	conn.commit()
	c.close()
	conn.close()

async def add_hints(message, client):
	numhints = int(message.content.split()[1])
	print(numhints)
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' INSERT into hints values(?)''', (numhints,))
	conn.commit() 

	c.execute(''' SELECT sum(num) from hints ''')
	total_hints = c.fetchall()[0][0]
	c.close()
	conn.close()

	await message.channel.send('added ' + str(numhints) + ' hints. The total is now ' + str(total_hints))

async def reg_team(message, client):
	team_name =  re.findall('name:`#?(?P<ch>.*?)`', message.content)[0]
	channel = await message.guild.create_text_channel(team_name, category=message.channel.category)
	modrole = message.guild.get_role(int(meta[4]))
	await channel.set_permissions(modrole, read_messages=True, send_messages=True)
	for user in message.mentions:
		await channel.set_permissions(user, read_messages=True, send_messages=True)
	await channel.set_permissions(message.guild.me, read_messages=True, send_messages=True)
	await channel.set_permissions(message.guild.default_role, read_messages=False, send_messages=False)

	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' INSERT into teams values(?,?,?)''', (team_name,channel.id,0))
	conn.commit()
	c.execute(''' SELECT puzzle_name from puzzles where unlocked_at=0''')
	puzzles = [x[0] for x in c.fetchall()]
	for puzzle in puzzles:
		c.execute(''' INSERT into events values(?,?,?,?,?,?)''', (0, 'unlock', team_name, 0, puzzle, ''))
		await channel.send('Puzzle unlocked: '+puzzle)
		conn.commit()
	c.close()
	conn.close()
	await message.channel.send('successfully registered team '+team_name)



general_commands = {'help':send_help, 'goto': send_puzzle, 'guess':process_guess, 
					'hint':process_hint, 'status':send_status, 'leaderboard':send_lb, 'lb':send_lb}

admin_commands = {'sudo':sudo, 'pause':0, 'unpause':0, 'register_team':reg_team, 'add_hints':add_hints, 'rt':reg_team}


def run_admin_command(message, client):
	pass

@client.event
async def on_message(message):
	if message.author != message.guild.me:
		for cmd in general_commands.keys():
			if cc+cmd in message.content:
				team = Team(message, client)
				await general_commands[cmd](team)
				break 
		for cmd in admin_commands.keys():
			if cc+cmd in message.content and message.author.id in auth_admins:
				await admin_commands[cmd](message, client)
				break 


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

client.run(token)
