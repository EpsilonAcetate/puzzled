import discord
import sqlite3
import datetime
import re
from classes import *
import random

meta = open('meta.txt').read().split()
token = meta[0]
dbname = meta[1]
hintchannel_ID = int(meta[2])
admin_IDs = meta[3]

client = discord.Client()
cc = '!' # command character

auth_admins = [int(x) for x in admin_IDs.split(',')]

def ismeta(p):
	return p=='meta'

async def send_help(team):
	helptext = open('helptext.txt').read().split('--------')
	await team.channel.send(helptext[0])

async def admin_help(message, client):
	helptext = open('helptext.txt').read().split('--------')
	await message.channel.send(helptext[1])

async def send_puzzle(team):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()

	name = team.content[1].lower()
	if name in team.unlocked_puzzles: 
		c.execute('''SELECT link from puzzles where puzzle_name=?''', (name,))
		puzzlelink = c.fetchall()[0][0]
		await team.channel.send(f"{name}: {puzzlelink}")
	else:
		await team.channel.send("That was either not a valid puzzle, or you haven't unlocked the puzzle yet. Use "
								"`!help` for command syntax.")

async def process_guess(team):

	if team.paused == 1:
		await team.channel.send("You've been going through too many test subjects and have been temporarily put on "
								"hold while the lab processes the backlog of requests.\nTranslation: You're currently prevented from guessing. Please wait until a TA unpauses you to resume. ")
		return 

	conn = sqlite3.connect(dbname)
	c = conn.cursor()

	puzzle = team.content[1].lower()
	guess = team.content[2].lower()
	if puzzle in team.solved_puzzles:
		await team.channel.send(f"Aw that is exactly right, but you've been exactly this right before. \n Translation: "
								f"You've already solved the {puzzle} puzzle! Pack up your medical bags and try a "
								f"different room.")
	elif puzzle in team.unlocked_puzzles: 
		c.execute('''SELECT answer, close_answers from puzzles where puzzle_name=?''', (puzzle,))
		answers = c.fetchall()[0]
		print(answers)
		answer = answers[0]
		close_answers = answers[1].split()

		print(answer, guess)

		if answer == guess:
			await team.channel.send(f"You absolute mad(wo)man! That is so correct ima cry.\nCongratulations on "
									f"solving the {puzzle} puzzle!")
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'solve', team.name, team.now, puzzle, ''))
			conn.commit()
			c.execute(''' SELECT puzzle_name from puzzles where unlocked_at=? ''', (len(team.solved_puzzles)+1,))
			unlocked_puzzles = [x[0] for x in c.fetchall()]
			for p in unlocked_puzzles:
				c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'unlock', team.name, team.now, p, ''))
				if ismeta(p):
					await team.channel.send(f"After much internal arguing and gathering of mental strength, you dare to "
											f"approach the front door once more.\nTranslation: Congratulations on solving "
											f"5/6 base puzzles and unlocking the meta! You can now use `!status` to see "
											f"the {p} puzzle.")
				else: 
					await team.channel.send(f"Congrats, you've unlocked the intermediate puzzle {p}! You can now use `!status` to see the {p} puzzle.")
			if ismeta(puzzle):
				await team.channel.send("After much fiddling and a combination of guesswork and pure genius, "
										"you and your trusty teammates have finally derived the cure for COVID-19! It also seems to cure just about any ailment, the new \"magic bullet\" of the world if you will, and you proudly present your cure to the world to see! Just then, you realize that you were but one of the many simulations scraping the web for a suitable cure in the great Game of Life.\nCongratulations on solving the final puzzle and completing the hunt! You're welcome to continue solving any remaining puzzles (for use in tiebreaking or just for fun).")
		elif guess in close_answers:
			await team.channel.send("Close but no cigar! Not that you should make your health worse...\nTranslation: You're on the right track. Keep going!")
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'guess', team.name, team.now, puzzle, guess))

		else:
			await team.channel.send("Hmm...maybe...possibly...no.\nTranslation: Sorry, this is incorrect. Please try "
									"again.")
			c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'guess', team.name, team.now, puzzle, guess))
		conn.commit()
	else:
		await team.channel.send("That was either not a valid puzzle, or you haven't unlocked the puzzle yet. Use "
								"`!help` for command syntax.")
	c.close()
	conn.close()

async def process_hint(team):
	hint_text = team.message.content 
	puzzle = team.content[1]
	hint_content = ' '.join(team.content[2:])

	if team.hints_remaining <= 0: 
		await team.channel.send('Sorry, you have no more hints remaining. Please wait until more hints are released!')
	elif puzzle in team.solved_puzzles:
		await team.channel.send(f"You've already cracked the code, parsed the puzzle, solved the cipher, defeated the deception, revealed the ruse, uncovered the uncertainty.\nTranslation: You've already solved the {puzzle} puzzle! Use hints on unsolved puzzles.")
	elif puzzle in team.unlocked_puzzles:
		conn = sqlite3.connect(dbname)
		c = conn.cursor()

		request = f"**Team**: {team.name}\n**Puzzle**: {puzzle}\n**Link**{team.message.jump_url}\n```{hint_content}```"
		hint_channel = team.client.get_channel(hintchannel_ID)
		c.execute(''' INSERT INTO events VALUES(?,?,?,?,?,?)''', (1, 'hint', team.name, team.now, puzzle, hint_content))
		conn.commit()
		s1 = "rented an electric scooter and rode up and down every street in Pittsburgh until you found a house with a ridiculous amount of construction equipment and a BLM sign and then went inside and had some peppermint tea (we don't care if you don't like peppermint tea) and asked an overworked TA your questions."
		s2 = "ordered Chinese food to be sent to one lucky TA and had written your question inside a fortune cookie " \
			 "for them to read."
		s3 = "bribed an easily pleased TA with a very good ascii depiction of one giant cat (it's very cute)."
		s4 = "showed up at Ping-Ya's house at 4am pounding on the windows, which unfortunately isn't enough to " \
			 "wake Ping-Ya from her dreams of giant lollipop soldiers, but it causes all the neighbors to call the " \
			 "cops, and the sirens wake up Ping-Ya, and Ping-Ya assumes they've found out about her hacking into " \
			 "private company databases so she dashes to her car and the cops begin a high speed pursuit through NC, " \
			 "and Ping-Ya finally loses them and pulls off to a back road, where you happen to be waiting to ask her " \
			 "your question."
		s5 = "single handedly developed true artificial intelligence while also solving the P vs NP problem, " \
			 "make millions of dollars and win a Nobel prize and a Turing award, travel to Hollywood, become a world " \
			 "famous actor, win 3.5 Oscars, move to one of your many islands, live completely alone, feel completely " \
			 "regretful of your life decisions and how you never quite understood the HW4 instructions, " \
			 "invent a time machine, travel back and meet Sean on gates 5 at exactly 9:42pm, ask him your questions, " \
			 "go back to the future, die alone and leave all of your wealth to a parrot named Todd."
		s6 = "built a moat around David's house, gathered a Roman army, attempted to cross the moat you just built " \
			 "with your army, being unsuccessful except for one young boy named Chad (very Roman name) who managed to make it across, and instructing Chad to ask David your question (which he will obviously have to communicate back to you across the moat, but who knows if he'll make it back across safely, so you'll have to figure out that part)."
		s7 = "trained a chipmunk to speak English (Alvin, Theodore, or the other one) and asked them to run to " \
			 "Rebecca's house in Pittsburgh and deliver your question."
		s8 = "send 12 drummers drumming to Alan's house to play your question on drums in morse code (while standing " \
			 "at least 6 feet apart from each other and from him). "
		s9 = "created a 4 minute long YouTube video of you asking your question in slow motion."
		s10 = "bought some very bright lasers took a long-exposure photo of you writing out your question with " \
			  "frantic laser waving such that it became an artistic masterpiece and was publihed in a world-renowned " \
			  "magazine that Alan happened to read while in the waiting room of one very important individual, " \
			  "causing him to ditch his pre-scheduled meeting and frantically ponder a response."
		s11 = "collected a bunch of dead branches by the sea of a deserted island and started a bomfire on the shore. By waving a blanket over the flames like an intense matador, you manage to send your question via smoke signal just as the blanket catches on fire."
		hintText = random.choice([s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11])
		await team.channel.send(f"You've {hintText}\nA TA will materialize with a hint soon~\n\nYou have {team.hints_remaining-1}/{team.total_hints} hints remaining.")
		await hint_channel.send(request)
		c.close()
		conn.close()

	else: 
		await team.channel.send("That was either not a valid puzzle, or you haven't unlocked the puzzle yet. Use "
								"`!help` for command syntax.")


async def send_status(team):
	embed=discord.Embed(title="Status - "+team.name, color=0x0)
	unsolved = "\n".join([ f"[{x}]({y})" for (x,y,z) in team.unsolved])
	if unsolved == "":
		unsolved = '-'
	embed.add_field(name="Unsolved puzzles: ", value=unsolved, inline=False)
	solved = "\n".join([ f"[{x}]({y}) ({z.upper()})" for (x,y,z) in team.solved])
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

async def send_lb_admin(message, client):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' SELECT team_name, count(*), MAX(timestamp) from events where type='solve' group by team_name order by count(*) desc, MAX(timestamp)''')
	lb = c.fetchall()

	embed=discord.Embed(title="Leaderboard", color=0x0)

	rank=1
	for (teamname, n, ts) in lb:
		embed.add_field(name=f"#{rank}: {teamname}", value=f"{n} puzzles solved, latest solve {ts}", inline=False)
		rank = rank+1

	await message.channel.send(embed=embed)

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
	await message.channel.send(f'Set paused-ness of team `{team_name}` to `{effect}`.')

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

	await message.channel.send(f'Added {numhints} hints for each team. The total is now {total_hints} hints.')

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
		await channel.send(f"{puzzle} puzzle unlocked! You can now use `!status` to see the {puzzle} puzzle.")
		conn.commit()
	c.close()
	conn.close()
	await message.channel.send(f"Registered team `{team_name}`.")


async def reset(message, client):
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute(''' DELETE FROM teams''')
	conn.commit()
	c.execute(''' DELETE FROM events''')
	conn.commit()
	c.execute(''' DELETE FROM hints''')
	conn.commit()
	c.execute(''' INSERT INTO hints VALUES(2)''')
	conn.commit()
	c.close()
	conn.close()

general_commands = {'help':send_help, 'goto': send_puzzle, 'guess':process_guess, 
					'hint':process_hint, 'status':send_status, 'leaderboard':send_lb, 'lb':send_lb}

admin_commands = {'sudo':sudo, 'pause':pause_team, 'unpause':unpause_team, 'register_team':reg_team, 
					'add_hints':add_hints, 'rt':reg_team, 'reset':reset, 'adminhelp':admin_help, 'lb2':send_lb_admin}


@client.event
async def on_message(message):
	if message.author != message.guild.me:
		for cmd in general_commands.keys():
			if cc+cmd in message.content:
				team = Team(message, client)
				await general_commands[cmd](team)
				break 
		for cmd in admin_commands.keys():
			if cc+cmd in message.content and message.author.id in auth_admins and message.channel.id==hintchannel_ID:
				await admin_commands[cmd](message, client)
				break 


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)

client.run(token)
