#
#   Token contract source code must be uploaded and verified on BSCscan or we'll have hard time retrieving name, decimals etc
#

from web3 import Web3
import csv, datetime, requests, json, time

#  CSV format
# [wallet address], [amount], ..any additional data ignored (compatible with holder CSV files exported from bscscan.com)
# "0xe23eb27bc46dbbc08529dbe94db108117e548623","5162368946.03815"
csv_file_name = "sample_holders_42.csv"

# list of wallets excluded from distiobution, i.e. burn address, LP address etc (add and remove as needed)
excluded_list = ["0x000000000000000000000000000000000000dead",
                 "0x0000000000000000000000000000000000000001"]

# information of TOKEN we are distributing
token_contract = "0x636969_YOUR_TOKEN_CONTRACT_ADDRESS"						# !!! CHANGE THIS 


# distribution wallet address and PRIVATE KEY
dist_wallet            = "0x8942_____DISTRIBUTUTION_WALLET_ADDRESS"				# !!! CHANGE THIS
DIST_KEY               = "e7__________________DISTRIBUTION_WALLET_PRIVATE_KEY____"		# !!! CHANGE THIS

minimum_BNB_balance    = 0.002    # if distribution wallet's balance falls bellow specified, airdrop stops
minimum_TOKEN_balance  = 10000.0  # if distribution wallet's balance falls bellow specified, airdrop stops


log_file = "air_drop" # + "[date_stamp].log"

# chain selection
#bsc = "https://bsc-dataseed.binance.org/"               # MAINNET for BSC Binance Smart Chain (more info https://docs.binance.org/smart-chain/developer/rpc.html)
bsc = "https://data-seed-prebsc-1-s1.binance.org:8545/"  # TESTNET for BSC Binance Smart Chain (more info https://docs.binance.org/smart-chain/developer/rpc.html)

#bscscan = "https://api.bscscan.com/api"                 # BSCscan mainnet
bscscan = "https://api-testnet.bscscan.com/api"          # BSCscan testnet



# distribute fixed amount of token OR specified amounts in csv file
fixed_amount = True
# if fixed_amount = True:
amount_sending = 100.0

# sleeping 10 seconds between transactions. to make it reliably faster it needs to burn more gas and/or wait for tx confirmation [not implemented]
tx_sleep_time = 10




#####################################################################################################

def valid_address(addyStr):
  if len(addyStr) == 42 and addyStr.startswith('0x'):
    return True
  else:
    return False



def load_address_list(csv_file):
  holders = []
  with open(csv_file, newline='') as f:
    reader = csv.reader(f)
    holders = list(reader)
  
  #clear list 
  cleared_holders = []
  for entry in holders:
    if valid_address(entry[0]):
      cleared_holders.append(entry)
  return cleared_holders



def send_tokens(token_contract, sender, recipient, amount, private_key):
  key_account       = web3.eth.account.privateKeyToAccount(private_key)
  sender_checked    = web3.toChecksumAddress(sender)
  recipient_checked = web3.toChecksumAddress(recipient)

  nonce = web3.eth.get_transaction_count(key_account.address)
  transaction = token_contract.functions.transfer(recipient_checked, amount).buildTransaction({
              'gas': 200000,
              'gasPrice': web3.toWei('11', 'gwei'),
              'from': sender_checked,
              'nonce': nonce
              }) 
  signed_txn = web3.eth.account.signTransaction(transaction, private_key=private_key)
  tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
  return tx_hash



if __name__ == "__main__": 
  # generate name for logs file
  timeNow = datetime.datetime.now()
  logFileStamp = timeNow.strftime("%Y_%m_%d")
  log_file_name = log_file +"_"+logFileStamp+".log"


  # load wallet addresses from csv file
  holder_list = load_address_list(csv_file_name)


  # initializing WEB3
  web3 = Web3(Web3.HTTPProvider(bsc))
  print("[BSC_AirDrop] BSC Web3 connection status: ", web3.isConnected())

  #get token contract ABI
  contract_checked = web3.toChecksumAddress(token_contract)
  API_ENDPOINT = bscscan+"?module=contract&action=getabi&address="+str(contract_checked)

  # saving some cookies with sessions
  user_agent = {'User-agent': 'Mozilla/5.0'}
  session = requests.Session()                     
  rec = session.get(API_ENDPOINT, headers = user_agent) 
  cookies = dict(rec.cookies)                

  r = session.get(API_ENDPOINT, headers = user_agent, verify=False, cookies=cookies)
  response = r.json()
  abi=json.loads(response["result"])
  contract = web3.eth.contract(address=contract_checked, abi=abi)

  
  # get token contract details and balances
  token_dec = contract.functions.decimals().call()
  token_sym = contract.functions.symbol().call()
  token_nm = contract.functions.name().call()
  print("------------------------------------------------")
  print("Token: ",token_sym, " decimals: ", token_dec)


  # get DISTRIBUTION WALLET's BNB balance
  wei_balance = web3.eth.get_balance(dist_wallet)
  bnb_balance = wei_balance / (10 ** 18)
  print("Distribution wallet address: ", dist_wallet)
  print("BNB balance: ", wei_balance, "wei    [",'{:,.6f}'.format(bnb_balance)," BNB ]")

  # get DISTRIBUTION WALLET's token balance
  token_raw_balance = contract.functions.balanceOf(dist_wallet).call()
  token_balance = token_raw_balance / (10 ** token_dec)
  print("Token balance: ", token_raw_balance, "raw    [",'{:,.6f}'.format(token_balance)," ",token_sym," ]")
  print("------------------------------------------------")


  # begin distribution
  total_rec = len(holder_list)
  print("Total number of records loaded: ", total_rec)
  # ask for starting point, for new session it's usually always 0
  start_index = int(input("Enter starting index (0-"+str(total_rec-1)+"), should be 0 for new session: "))
  while start_index < 0 or start_index > (total_rec-1):
    print("Out of range!")
    start_index = int(input("Enter starting index (0-"+str(total_rec-1)+"), should be 0 for new session: "))


  # format all excluded wallets to lowcase 
  excluded_lowcase = []
  for ady in excluded_list:
    excluded_lowcase.append(ady.lower())

  ix = 0
  for record in holder_list:
    #skipping all records until index, if starting index was not 0
    if (ix >= start_index) and (record[0].lower() not in excluded_lowcase):
      #get bnb and token balance of distribution wallet, proceeding if balances still above minimum
      wei_balance = web3.eth.get_balance(dist_wallet)
      bnb_balance = wei_balance / (10 ** 18)
      token_raw_balance = contract.functions.balanceOf(dist_wallet).call()
      token_balance = token_raw_balance / (10 ** token_dec)
      if bnb_balance < minimum_BNB_balance or token_balance < minimum_TOKEN_balance:
        print("Distribution wallet's BNB / TOKEN balance bellow specified minumum. Cannot proceed.")
        print("BNB: ", bnb_balance, "   Minimum :",minimum_BNB_balance)
        print("Token: ", token_balance, "   Minimum :",minimum_TOKEN_balance)
        break
      else:
        # if distributing fixed amount, then will send amount specified, otherwise taking amounts as they are in CSV file next to address
        if fixed_amount:
          amount2send = amount_sending
        else:
          amount2send = float(record[1])

        #converting human readable float token amount to RAW format with no decimal point
        amount_raw = int(amount2send * (10 ** token_dec))
        send2address = record[0]
        print("[tx",ix,"] Sending", '{:,.6f}'.format(amount2send), token_sym, "  to: ", send2address,"...")
        result = send_tokens(contract, dist_wallet, send2address, amount_raw, DIST_KEY) 
        print("TX hash: ", result.hex())

        #log it
        timeNow = datetime.datetime.now()
        timeStampStr = timeNow.strftime("[%d-%b-%Y %H:%M:%S]")
        log_line = timeStampStr+",index["+str(ix)+"],"+send2address+","+str(amount_raw)+",TXHASH:"+result.hex()+"\n"
        with open(log_file_name, "a+") as log_file:
          log_file.write(log_line)

        time.sleep(tx_sleep_time) 
    ix = ix + 1   
 
