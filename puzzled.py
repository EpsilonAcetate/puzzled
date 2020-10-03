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

	if team.paused == 1:
		await team.channel.send('you are currently paused')
		return 

	conn = sqlite3.connect(dbname)
	c = conn.cursor()

	puzzle = team.content[1].lower()
	guess = team.content[2].lower()
	if puzzle in team.solved_puzzles:
		await team.channel.send("puzzle already solved")
	elif puzzle in team.unlocked_puzzles: 
		c.execute('''SELECT answer, close_answers from puzzles where puzzle_name=?''', (puzzle,))
		answers = c.fetchall()[0]
		print(answers)
		answer = answers[0]
		close_answers = answers[1].split()

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
		elif guess in close_answers:
			await team.channel.send('almost right')
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'guess', team.name, team.now, puzzle, guess))
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
	embed=discord.Embed(title="Status - "+team.name, color=0x0)
	unsolved = ", ".join([ f"[{x}]({y})" for (x,y,z) in team.unsolved])
	if unsolved == "":
		unsolved = '-'
	embed.add_field(name="Unsolved puzzles: ", value=unsolved, inline=False)
	solved = ", ".join([ f"[{x}]({y}) ({z.upper()})" for (x,y,z) in team.solved])
	if solved == '':
		solved = '-'
	embed.add_field(name="Solved puzzles: ", value=solved, inline=False)
	embed.add_field(name="Hints used: ", value=team.hints_used)	
	embed.add_field(name="Hints remaining: ", value=team.hints_remaining)


	await team.channel.send(embed=embed)


async def send_lb(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' SELECT team_name, count(*), MAX(timestamp) from events where type='solve' group by team_name order by count(*) desc, MAX(timestamp)''')
	lb = c.fetchall()

	embed=discord.Embed(title="Leaderboard", color=0x0)

	rank=1
	for (teamname, n, ts) in lb:
		embed.add_field(name=f"#{rank}: {teamname}", value=f"{n} puzzles solved, latest solve {ts}", inline=False)
		rank = rank+1

	await team.channel.send(embed=embed)

async def sudo(message, client): 
	query = re.findall('```(?P<ch>.*?)```', message.content)[0]
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(query)
	conn.commit()
	c.close()
	conn.close()

async def pause_team(message, client, effect=1):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	team_name = re.findall('name:`#?(?P<ch>.*?)`', message.content)[0]
	c.execute(''' SELECT channel_ID, paused from teams where team_name=? ''', (team_name,))
	teaminfo = c.fetchall()[0]
	c.execute(''' DELETE FROM teams where team_name=?''', (team_name,))
	c.execute(''' INSERT INTO teams values(?,?,?) ''', (team_name, teaminfo[0], effect))
	conn.commit()
	c.close()
	conn.close()
	await message.channel.send(f'set pausedness of team to {effect}')

async def unpause_team(message, client):
	await pause_team(message, client, effect=0)


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

admin_commands = {'sudo':sudo, 'pause':pause_team, 'unpause':unpause_team, 'register_team':reg_team, 'add_hints':add_hints, 'rt':reg_team}


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
