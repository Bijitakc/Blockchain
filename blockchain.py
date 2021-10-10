import hashlib
import json
from time import time


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []

        #create a genesis block(first block without predecessors)
        self.new_block(previous_hash = 1, proof = 100)

    
    #creates a new block and adds it to the chain
    def new_block(self, proof, previous_hash = None):
        """
        proof : <int> The proof given by proof of work algorithm
        previous_hash : (optional) Hash of previous block
        """
        #block
        block = {
            'index' : len(self.chain) + 1 ,
            'timestamp' : time() ,
            'transactions' : self.current_transactions,
            'proof' : proof ,
            'previous_hash' : previous_hash or self.hash(self.chain[-1])
        }

        #Reset the curent list of transactions
        self.current_transactions = []
        self.chain.append(block)
        return block

    #creates a new transaction to go into the next mined block
    def new_transaction(self, sender, recipient, amount):
        """
        sender,recipient : <str> Address of the sender, recipient
        amount : <int>  Transaction Amount
        """

        self.current_transactions.append({
            'sender' : sender,
            'recipient' : recipient,
            'amount' :  amount,
        })

        return self.last_block['index'] + 1

    #creates a hash of the block using SHA-256
    @staticmethod
    def hash(block):
        print(block)
        #We must make sure that the dictionary is ordered or we will have inconsistent hashes
        block_string = json.dumps(block, sort_keys = True).encode
        #the following line hashes the block_String and hexdigest returns it in hexadecimal format
        return hashlib.sha256(block_string).hexdigest()

    #returns last block in chain
    @property
    def last_block(self):
        return self.chain[-1]

    





    