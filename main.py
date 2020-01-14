from fbchat import Client, ThreadType, Message, VideoAttachment, ImageAttachment
from termcolor import colored
from getpass import getpass
import colorama
import sentry_sdk
import os
import pickle
import requests
import time
import codecs  # https://stackoverflow.com/questions/30469575/how-to-pickle-and-unpickle-to-portable-string-in-python-3
import DB

colorama.init()
sentry_sdk.init("https://ddc9dbf023ba4e30b241b74ad7b7efcb@sentry.io/1520935")
db = DB.DB()
client = None
#re_listen_point = 1403


class Keeper(Client):
	def load_user_name_by_id(self, uid):
		user_name = db.loda('ids', uid)
		if user_name is None:
			user_name = uid
			await_users = self.fetchUserInfo()
			users = list(await_users.values())
			for user in users:
				user_name = user.name
				db.seva('ids', user.id, user.name)
		return user_name

	def load_group_name_by_id(self, gid):
		group_name = db.loda('ids', gid)
		if group_name is None:
			group_name = gid
			await_groups = self.fetchGroupInfo()
			groups = list(await_groups.values())
			for group in groups:
				group_name = group.name + \
					" - {} participants".format(len(group.participants))
		return group_name


	def on_message(self, mid=None, author_id=None, message_object=None, thread_id=None, thread_type=None, at=None, metadata=None, msg=None):
		print(colored("Received new message", 'green'))
		print(message_object)
		key = message_object.uid.replace('.$', '_')
		value = codecs.encode(pickle.dumps(message_object), 'base64').decode()
		# print("Saving...\nkey -> [{}]\nvalue -> [{}]".format(key, value))
		db.seva('messages2', key, value)
		if author_id == self.uid and message_object.text == "#off":
			if loop.stop():
				print(colored('SAFETY LOGOUT RETURNED NON-ZERO', 'white', 'on_blue'))
			else:
				print(colored('SAFETY LOGOUT RETURNED ZERO', 'white', 'on_green'))

	def onMessage(self, mid=None, author_id=None, message=None, message_object=None, thread_id=None, thread_type=ThreadType.USER, ts=None, metadata=None, msg=None):
		self.on_message(mid, author_id, message_object, thread_id, thread_type, ts, metadata, msg)

	def on_message_unsent(self, mid=None, author_id=None, thread_id=None, thread_type=None, at=None, msg=None):
		print(colored("{} removed a message on {} {}".format(
			author_id, thread_type, thread_id), 'magenta'))
		# print("id -> {}".format(mid))
		pickled = db.loda('messages2', mid.replace('.$', '_'))
		removed_msg = pickle.loads(codecs.decode(pickled.encode(), 'base64'))
		print(removed_msg)
		# fetch attachments
		media_urls = []
		other_attachment_urls = ""
		other_attachment_ids = []
		if removed_msg.attachments:
			for item in removed_msg.attachments:
				if(isinstance(item, (VideoAttachment, ImageAttachment, ))):
					url = self.fetchImageUrl(item.uid)
					media_urls.append(url)
				else:
					other_attachment_urls += item.url + "\n"
					other_attachment_ids.append(item.uid)
		print(colored("fetch attachment done!", 'green'))
		user_name = self.load_user_name_by_id(author_id)
		print("username -> [{}]".format(user_name))
		if thread_type == ThreadType.GROUP:
			thread_name = self.load_group_name_by_id(thread_id)
		else:
			thread_name = 'INBOX'
		print("thread_name -> [{}]".format(thread_name))
		msg = "{} removed a message in [{}]\n".format(user_name, thread_name)
		replied_to = "\n* -> [{}]".format(removed_msg.text)
		if removed_msg.attachments:
			replied_to += "\n{} attachment(s)".format(len(removed_msg.attachments))
		if removed_msg.replied_to:
			replied_to += "\nreplied to {} -> [{}]".format(self.load_user_name_by_id(removed_msg.replied_to.author), removed_msg.replied_to.text)
			if len(removed_msg.replied_to.attachments):
				replied_to += " {} attachments".format(
					len(removed_msg.replied_to.attachments))
		msg += replied_to
		self.send(Message(text=msg, sticker=removed_msg.sticker), thread_id=self.uid)
		if len(media_urls) or len(other_attachment_urls): self.sendRemoteFiles(media_urls, other_attachment_urls, self.uid)
		if len(other_attachment_ids):
			for attachment_id in other_attachment_ids:
				self.forwardAttachment(attachment_id, self.uid)

	def onMessageUnsent(self, mid=None, author_id=None, thread_id=None, thread_type=None, ts=None, msg=None):
		self.on_message_unsent(mid, author_id, thread_id, thread_type, ts, msg)


def start():
	global client
	print("Logging in...")
	session = None
	if os.path.isfile('fb_session'):
		with open('fb_session', 'rb') as f:
			session = pickle.load(f)
	client = Keeper(input("facebook username: "), getpass("facebook password: "), session_cookies = session)
	with open('fb_session', 'wb') as f:
		pickle.dump(client.getSession(), f)
	time.sleep(1)
	print("Hello, i'm MessageKeeper, i'm listening...")
	client.listen()
	print(colored("listen completed!", 'white', 'on_red'))
	# while True:
	# 	if client.is_logged_in():
	# 		client.send(Message(text = "Message Keeper logged in & listening..."), thread_id = client.uid)
	# 		client.listen()
	# 		client.send(Message(text = "Message Keeper listen cycle done! trying to re-listen..."), thread_id = client.uid)

start()