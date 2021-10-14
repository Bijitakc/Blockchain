import json
import hashlib
from urllib import parse
import uuid
import sys
import psycopg2
from time import time
from uuid import uuid4
from textwrap import dedent
from urllib.parse import urlparse
from flask import Flask, jsonify, request

#To connect to database
from db_info import DB_HOST, DB_NAME, DB_USER, DB_PASS

conn = psycopg2.connect(dbname = DB_NAME, user = DB_USER, password = DB_PASS, host = DB_HOST)


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #create a genesis block(first block without predecessors)
        self.new_block(previous_hash = 1, proof = 100)
    
    def register_node(self, address):
        parsed_url = urlparse(address)
        print(parsed_url)
        self.nodes.add(parsed_url.netloc)
        print(parsed_url.netloc)

    #to determine if the chain is valid
    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            
            last_block = block
            current_index += 1

        return True

    #Consensus algo that resolves conflicts by replacing chain with thelongest most valid one
    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        #grab and verify all the chains from the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                #check if the length is longer and the chain is valid
                if length>max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        
        return False

    def proof_of_work(self, last_proof):
        """
        A pow algorithm as follows:
        - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
        - p is the previous proof, and p' is the new proof

        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof +=1

        return proof
    
    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"
    
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
        cur = conn.cursor()
        # cur.execute("INSERT INTO postgres (block) VALUES (%s)", ("sdcfvg",))
        # cur.execute("CREATE TABLE blockchain (index SERIAL PRIMARY KEY, timestamp TIMESTAMP, proof VARCHAR);")
        conn.commit()
        cur.close()
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
        print("lol", file=sys.stderr)
        #We must make sure that the dictionary is ordered or we will have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        print(type(block_string))
        return hashlib.sha256(block_string).hexdigest()

    #returns last block in chain
    @property
    def last_block(self):
        return self.chain[-1]

    #Flask portion

#Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

#Instantiate blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    # print("hi")
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # print("here")
    # print(last_block, last_block, proof)
    #sender is 0 symbolizes that this node has mined a new coin
    blockchain.new_transaction(
        sender = "0",
        recipient = node_identifier,
        amount = 1,
    )

    #forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message' : "New Block Forged",
        'index' : block['index'],
        'transactions' : block['transactions'],
        'proof' : block['proof'],
        'previous_hash' : block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # print("hola", file=sys.stderr )
    values = request.get_json()
    # print(values, file=sys.stderr )

    #check that the required fields are in the POSTed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400     
    #creating a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message' : f'Transaction will be added to Block{index}'}
    return jsonify(response), 201 

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
            'length' : len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values['nodes']

    if nodes is None:
        return "Error: The input is invalid", 400

    for node in nodes:
        blockchain.register_node(node)
    
    response = {
        'message' : "The nodes have been added",
        'total_nodes' : list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message' : 'Our chain was replaced',
            'new_chain' : blockchain.chain
        }
    else:
        response = {
            'message' : 'Our chain is valid.',
            'chain' : blockchain.chain
        }
    return jsonify(response), 200


if __name__ == '__main__':

    #python file.py -p PORTNUMBER
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)
    

    