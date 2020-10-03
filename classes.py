import discord
import sqlite3
import datetime

meta = open('meta.txt').read().split()
dbname = meta[1]

class Team():
	def __init__(self, message, client): 
		# attributes: 
		#	channel (channel object), client (client object)
		# 	team_ID, name, channel_ID, num_hints, paused
		#	solved_puzzles, unlocked_puzzles, unsolved_puzzles

		self.message = message
		self.channel = message.channel
		self.client = client

		self.content = message.content.split(' ')

		conn = sqlite3.connect(dbname)
		c = conn.cursor()
		c.execute('''SELECT team_name, channel_ID, paused FROM teams WHERE channel_ID=?''', (self.channel.id,))
		res = c.fetchall()[0]

		self.name, self.channel_ID, self.paused = res[0], res[1], res[2]

		c.execute(''' SELECT count(*) from events where events.team_name=? AND type='hint' ''', (self.name,))
		self.hints_used = c.fetchall()[0][0]
		print(self.hints_used)

		c.execute(''' SELECT sum(num) from hints ''')
		self.total_hints = c.fetchall()[0][0]
		print(self.total_hints)

		self.hints_remaining = self.total_hints - self.hints_used


		c.execute('''SELECT puzzles.puzzle_name, puzzles.link, puzzles.answer from events inner join puzzles on events.puzzle_name = puzzles.puzzle_name WHERE events.team_name=? AND events.type='solve' ''', (self.name,))
		self.solved = c.fetchall()
		print(self.solved)
		self.solved_puzzles = [x[0] for x in self.solved]

		c.execute('''SELECT puzzles.puzzle_name, puzzles.link, puzzles.answer from events inner join puzzles on events.puzzle_name = puzzles.puzzle_name WHERE events.team_name=? AND events.type='unlock' ''', (self.name,))
		self.unlocked = c.fetchall()
		self.unlocked_puzzles = [x[0] for x in self.unlocked]
		
		self.unsolved = list(set(self.unlocked) - set(self.solved))
		self.unsolved_puzzles = list(set(self.unlocked_puzzles) - set(self.solved_puzzles))
		
		c.close()

		#haha timezones go brr
		self.now = (message.created_at+datetime.timedelta(hours=-4)).isoformat(sep=' ', timespec='seconds')
		print(self.now)




# event types: solve, unlock, request-hint, guess