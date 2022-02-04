import json
import argparse
import requests
import datetime
import csv
import time
import re
import sys
import random


# Fixes/Updates by HelpingHand:
# -converted code to be fully compatible with Python3
# -API endpoints and json requests reworked to work with Liskv3
# -numerous code changes in order to accomodate for Liskv3
# -added feature to calculate actual delegate earnings (deduct voter share %)

# TODO:
# SHEER OVERKILL - Add a value calculation method to calculate actual token value at the time of forging (per block) and add this as an option
# Value calculation option: Per actual block or per day.

parser = argparse.ArgumentParser()
parser.add_argument("--network", help="use 'mainnet' or 'testnet'", choices=['mainnet', 'testnet', 'custom'])
parser.add_argument("--username", help="specify delegate username")
parser.add_argument("--share", help="specify voter's share")
parser.add_argument("--start", help="specify start date (yyyy/mm/dd)")
parser.add_argument("--end", help="specify end date (yyyy/mm/dd)")
args = parser.parse_args()


def setup_network():
	network_lookup = {	
	"mainnet": [
			"https://service.lisk.com",
			"https://mainnet-service.lisktools.eu",
				],
	"testnet": [
			"https://testnet-service.lisk.com",
			"https://testnet-service.lisktools.eu",
				],
	"custom": [
			"http://127.0.0.1:7000"
				]
	}

	if args.network is None:
		while True:
			print("Choose a network (mainnet / testnet)")
			answer = input("> ")
			answer_normalized = answer.lower().strip()		
			if answer_normalized in network_lookup:
				node = network_lookup[answer_normalized][random.randint(0, len(network_lookup[answer_normalized]) - 1)]
				network = answer_normalized
				break

	else:
		node = network_lookup[args.network][random.randint(0, len(network_lookup[args.network]) - 1)]
		network = args.network
	print("Using service node: %s" % node)
	node_status = get_json(node + "/network/status", True)
	return node, network


def setup_delegate():
	if args.username is None:
		print("\nEnter delegate username:")
		answer = input("> ")
		username = answer.strip()                     
	else:
		username = args.username.strip()
	
	if args.share is None:
		print("\nEnter voter's share (in %):")
		answer = input("> ")
		share = int(answer.strip(' %'))
		
	else:
		share = int(args.share.strip(' %'))
		
	try:
		delegate = get_json(node + "/api/v2/accounts?username=%s" % username)
		publickey = delegate['data'][0]['summary']['publicKey']
	except:
		sys.exit("Delegate not found.")

	address = delegate['data'][0]['summary']['address']
	delegate_name = username
	print("Delegate username %s found.\nAddress: %s\nSharing: %s percent\n" % (delegate_name, address, share))
	return address, publickey, delegate_name, share


def setup_filename(delegate_name):
	body = delegate_name + "_export_"
	creation_time = int(time.time())
	ext = ".csv"
	filename = body + str(creation_time) + ext

	return filename


def get_json(endpoint, is_alive_log=False):
	response = requests.get(endpoint)

	if response.status_code == 200:
		if is_alive_log:
			print("Node is alive :)\n")
	elif response.status_code == 429:
		print("Too many requests, exceeded rate limit.")
		sys.exit()
	elif response.status_code == 500:
		print("Unexpected error")
		sys.exit()

	return response.json()


def create_timestamp(date):
	try:
		return time.mktime(datetime.datetime.strptime(date, "%Y/%m/%d").timetuple())
	except ValueError as error:
		return error


def get_total_values(blockdata):
	lsk_total = 0.0
	btc_value = 0.0
	usd_value = 0.0
	eur_value = 0.0

	for block in blockdata:
		lsk_total += block[1]
		btc_value += block[2] * block[1]
		usd_value += block[3] * block[1]
		eur_value += block[4] * block[1]

	return lsk_total, btc_value, usd_value, eur_value


# Find the required amount of iterations to reach the nearest defined block (using timestamps)
def seek_block(date, mode, iterations_total):
	print("Seeking '%s' block..." % mode)

	iterations = 0
	offset = 0
	mult = 1
	timestamp_input = int(create_timestamp(date))# - LISK_EPOCH - no longer needed for timestamp calculations
	
	for i in range(iterations_total):
		json_data = get_json(node + "/api/v2/blocks?limit=1&offset=%s&generatorPublicKey=%s" % (offset, publickey))
		page_timestamp = json_data['data'][0]['timestamp']
		timestamp_diff = page_timestamp - timestamp_input
		
		if mode == "start" and timestamp_diff < 0:
			break
		if mode == "end" and timestamp_diff < 0:
			offset -= 100
			break		


		if timestamp_diff > 200000:
			mult = int(timestamp_diff / 200000)
		else:
			mult = 1	
		print ("Diff %s, %s = %s" % (timestamp_input, page_timestamp, timestamp_diff))
		print ("Pages jumped: %s" % mult)

		offset += int((100*mult))
		iterations += int((1*mult))
		# Prevent server ban by limiting API request rate
		time.sleep(0.02)

	return iterations, offset


print ('''
  ___    ___   __  __ 
 |   \  |_ _| |  \/  |
 | |) |  | |  | |\/| |
 |___/  |___| |_|  |_|  v1.3.0
  ''')        
print ("Delegate Income Monitor")
print ("Originally created by Lemii")
print ("Updated & improved to function with Liskv3 by HelpingHand")
print ("____________________________________\n")


# Setup stuff
node, network = setup_network()
address, publickey, delegate_name, share = setup_delegate()
filename = setup_filename(delegate_name)
v3_genesis_epoch = 1629547210 #Saturday, August 21, 2021 2:00:10 PM CET - Block 16270293

def main():

	forging_stats = get_json(node + "/api/v2/accounts?address=%s" % address)
	iterations_total = int(forging_stats['data'][0]['dpos']['delegate']['producedBlocks'] / 100) + 1
	blockstats =[]
	current_day = 0
	block_number = 0


	# Interactive wizard for start date
	if args.start is None:

		print ("(OPTIONAL) Enter start date (yyyy/mm/dd):\n")
		print ("Warning: If left empty, DIM will process *all* blocks ever")
		print ("forged by the delegate. This can take a very long time.\n")
		while True:
			answer = input("> ")
			if re.match(r'\d{4}/\d{2}/\d{2}', answer) != None:
                                # Add a check to deny dates before genesis block of Liskv3
				date_to_epoch = int(datetime.datetime.strptime(answer,"%Y/%m/%d").timestamp())
				if date_to_epoch >= v3_genesis_epoch:   
					start = answer
					break
				else:
					print("ERROR: You have chosen a date before the creation of the Liskv3 Genesis Block silly. Try again!\n\n(OPTIONAL) Enter start date (yyyy/mm/dd):")
			elif answer == "":
				start = None
				break
	else:
		start = args.start


	# Interactive wizard for end date
	if args.end is None and start is not None:
		while True:
			print ("(OPTIONAL) Enter end date (yyyy/mm/dd):")
			answer = input("> ")
			if re.match(r'\d{4}/\d{2}/\d{2}', answer) != None:
				end = answer
				break
			elif answer == "":
				end = None
				break
	else:
		end = args.end	


	# Calculate necessary amount of iterations (number of API result pages to go through)
	if start is not None:
		iterations_start, offset_start = seek_block(start, "start", iterations_total)
		print ("Start block found.\n")
		if end is not None:
			iterations_end, offset_end = seek_block(end, "end", iterations_total)
			print ("End block found.\n")
			offset = offset_end
			iterations_required = (iterations_start - iterations_end) + 1

		else:
			iterations_required = iterations_total - (iterations_total - iterations_start)
			offset = 0

	else: 
		iterations_required = iterations_total
		offset = 0


	#print ("Using offset: %s" % offset)
	#print ("Number of pages to process: %s (~%s blocks)\n" % (iterations_required, int(iterations_required) * 100))
	print ("Number of blocks to process: ~%s blocks\n" % (int(iterations_required) * 100))


	# Get block results (limited to 100 per page)
	for i in range(iterations_required):
		block_list = get_json(node + "/api/v2/blocks?limit=100&offset=%s&generatorPublicKey=%s" % (offset, publickey))
		# Retrieve data from each individual block of the result page
		for entry in block_list['data']:
			ignore = 0
			timestamp = int(entry['timestamp']) # REMOVED OBSOLETE LISK_EPOCH +
			if start != None and timestamp < create_timestamp(start):
				ignore = 1
				continue
			if start != None and end != None and timestamp > create_timestamp(end):
				ignore = 1
				continue

			date_time = datetime.datetime.fromtimestamp(timestamp).isoformat()
			date_time_simple = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
			day_as_int = datetime.datetime.fromtimestamp(timestamp).isoweekday()

			# Fetch LSK value data when switching to new day
			if day_as_int != current_day:
				try:
					cc_api_data = get_json("https://min-api.cryptocompare.com/data/pricehistorical?fsym=LSK&tsyms=BTC,USD,EUR&ts=%s" % timestamp)
					lsk_btc_value = cc_api_data['LSK']['BTC']
					lsk_usd_value = cc_api_data['LSK']['USD']
					lsk_eur_value = cc_api_data['LSK']['EUR']
					print ("LSK value at %s: %.8f BTC, %.2f USD, %.2f EUR" % (date_time_simple, lsk_btc_value, lsk_usd_value, lsk_eur_value))
				except: 
					lsk_btc_value = cc_api_data['LSK']['BTC']
					lsk_usd_value = cc_api_data['LSK']['USD']
					lsk_eur_value = cc_api_data['LSK']['EUR']
					print ("\nError fetching LSK value for %s" % date_time_simple)
				current_day = day_as_int
			
			if ignore != 1: 
				blockstats.append([date_time, float(entry['totalForged']) / 100000000, lsk_btc_value, lsk_usd_value, lsk_eur_value, entry['id']])
				message_string = "Retrieving data from block #%s, ID: %s" % (block_number, entry['id'])
			else:
				message_string = "Skipping block #%s, ID: %s" % (block_number, entry['id'])

			#sys.stdout.write('{0}\r'.format(message_string)) # If you like clutter, uncomment
			block_number += 1
			# Prevent server ban by limiting API request rate
			time.sleep(0.05)

		offset += 100


	print ("\n\nSummary:")
	#print ("Address: %s (%s)" % (address, delegate_name))
	#print ("Start / End date: %s - %s" % (start, end))
	lsk, btc, usd, eur = get_total_values(blockstats)

	print("Total LSK forged: {:0.8f}".format(lsk))
	print("Total BTC value: {:0.8f}".format(btc))
	print("Total USD value: {:0.2f}".format(usd))
	print("Total EUR value: {:0.2f}".format(eur))

	print("\nShared with voters: %s percent" % share)
	print("Voters LSK earned: {:0.8f}".format(lsk * (share / 100)))
	print("Voters BTC earned: {:0.8f}".format(btc * (share / 100)))
	print("Voters USD earned: {:0.2f}".format(usd * (share / 100)))
	print("Voters EUR earned: {:0.2f}".format(eur * (share / 100)))
	
	print("\nDelegate share: %s percent" % (100-share))
	print("Delegate LSK earned: {:0.8f}".format(lsk * ((100 - share) / 100)))
	print("Delegate BTC earned: {:0.8f}".format(btc * ((100 - share) / 100)))
	print("Delegate USD earned: {:0.2f}".format(usd * ((100 - share) / 100)))
	print("Delegate EUR earned: {:0.2f}".format(eur * ((100 - share) / 100)))


	# Write results to file
	with open(filename, "w") as f:
		f.write("Datetime\tLSK amount\tBTC value\tUSD value\tEUR value\tBlock ID\n")
		for row in blockstats:
			f.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (row[0], row[1], row[2], row[3], row[4], row[5]))
		print ("\nFile saved: %s" % filename)


	exit = input("\nPress [ENTER] key to exit")
	sys.exit()


if __name__ == '__main__':
	main()
