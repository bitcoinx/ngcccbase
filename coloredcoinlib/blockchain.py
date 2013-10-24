from bitcoinrpc import authproxy
import bitcoin.core

class COutpoint(object):
    def __init__(self, hash, n):
        self.hash = hash
        self.n = n

class CTxIn(object):
    def __init__(self, op_hash, op_n):
        self.outpoint = COutpoint(op_hash, op_n)

class CTxOut(object):
    def __init__(self, value):
        self.value = value

class CTransaction(object):

    def __init__(self, bs):
        self.bs = bs
        self.have_input_values = False

    @classmethod
    def from_jsonrpc(klass, d, bs):
        tx = CTransaction(bs)

        tx.hash = d['txid']
        tx.inputs = []
        for i in d['vin']:
            if 'coinbase' in i:
                tx.inputs.append(CTxIn('coinbase', 0))
            else:
                tx.inputs.append(CTxIn(i['txid'], i['vout']))
        tx.outputs = []
        for o in d['vout']:
            tx.outputs.append(CTxOut(long(o['value'] * 100000000)))
        return tx

    @classmethod
    def from_bitcoincore(klass, txhash, bctx, bs):
        tx = CTransaction(bs)

        tx.hash = txhash
        tx.inputs = []
        for i in bctx.vin:
            if i.prevout.is_null():
                tx.inputs.append(CTxIn('coinbase', 0))
            else:
                op = i.prevout
                tx.inputs.append(CTxIn(bitcoin.core.b2lx(op.hash),
                                       op.n))
        tx.outputs = []
        for o in bctx.vout:
            tx.outputs.append(CTxOut(o.nValue))
        return tx

    def ensure_input_values(self):
        if self.have_input_values:
            return
        for inp in self.inputs:
            prev_tx_hash = inp.outpoint.hash
            if prev_tx_hash != 'coinbase':
                prevtx = self.bs.get_tx(prev_tx_hash)
                inp.value = prevtx.outputs[inp.outpoint.n].value
            else:
                inp.value = 0 # TODO: value of coinbase tx?


class BlockchainState(object):
    def __init__(self, url):
        self.bitcoind = authproxy.AuthServiceProxy(url)
        self.cur_height = None

    def get_tx_state(self, txhash):
        try:
            raw = self.bitcoind.getrawtransaction(txhash, 1)
        except:
            return (None, False)
        if 'blockhash' in raw:
            block_data = self.bitcoind.getblock(raw['blockhash'])
            return (block_data['height'], False)
        else:
            return (None, True)

    def get_tx(self, txhash):
        txhex = self.bitcoind.getrawtransaction(txhash, 0)
        txbin = bitcoin.core.x(txhex)
        tx = bitcoin.core.CTransaction.deserialize(txbin)
        return CTransaction.from_bitcoincore(txhash, tx, self)

    def get_tx_old(self, txhash):
        return CTransaction.from_jsonrpc(self.bitcoind.getrawtransaction(txhash, 1), self)

    def iter_block_txs(self, height):
        txhashes = self.bitcoind.getblock(self.bitcoind.getblockhash(height))['tx']
        for txhash in txhashes:
            yield self.get_tx(txhash)

    def get_height(self):
        return self.cur_height
    def update(self):
        """make sure we use latest data"""
        self.cur_height = self.bitcoind.getblockcount() - 1
