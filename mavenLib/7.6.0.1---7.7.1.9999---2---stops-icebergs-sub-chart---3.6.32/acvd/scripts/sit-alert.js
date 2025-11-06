/*
Java code expects an object called "SIT"
The scrips should assume existence of the following global variables:
    alertsListener {
        void onAlert(String message);
    },
    indicatorListener {
        public void onUpdate(double value);
    }
    orderSizeFilter {
        boolean accept(long orderSize);
    }
*/

function Fifo() {
    this.array = new Array(16);
    this.head = 0;
    this.tail = 0;
    this.mod = this.array.length - 1;
    this.clear = function() { this.head = 0; this.tail = 0; }
    this.size = function()  { return this.tail - this.head; }
    this.first = function() { return (this.head === this.tail) ? null : this.array[this.head & this.mod]; }
    this.shift = function() { return (this.head === this.tail) ? null : this.array[this.head++ & this.mod]; }
    this.push = function(item) {
        if (this.head + this.array.length === this.tail) {
            var idx = this.head & this.mod;
            this.array = this.array.slice(idx).concat(this.array.slice(0, idx)).concat(new Array(this.array.length));
            this.head = 0;
            this.tail = this.array.length / 2;
            this.mod = this.array.length - 1;
        }
        this.array[this.tail++ & this.mod] = item;
    }
}

function Aggregator(period) {
    this.queue = new Fifo();
    this.cache = 0;
    this.period = period;
    this.add = function(t, x) {
        while (this.queue.size() > 0 && t - this.queue.first().t > this.period) {
            this.cache -= this.queue.shift().x;
        }
        this.queue.push({t: t, x: x});
        this.cache += x;
    }
    this.clear = function() {
        this.queue.clear() ;
        this.cache = 0;
    }
}

var aggressiveOrdersSizeFilter, passiveOrdersSizeFilter;

var SIT = {
    stops: new Aggregator(1e7),
    icebergs: new Aggregator(1e7),
    threshold: 50,
    msgId: 0,
    onTransaction: function(transaction) {
        var t = transaction.aggressiveOrder.timestamp;
        if (transaction.aggressiveOrder.isStop) {
            this.stops.add(t, transaction.aggressiveOrder.orderSize);
            if (aggressiveOrdersSizeFilter.accept(transaction.aggressiveOrder.orderSize)) {
                // TODO: update indicator's line;
            }
        }
        var tradeSizeIceberg = 0;
        for each (var passiveOrder in transaction.passiveOrders) {
            if (passiveOrder.isNativeIceberg) {
                this.icebergs.add(t, passiveOrder.tradeSize);
                if (passiveOrdersSizeFilter.accept(passiveOrder.lifetimeTradedSize + passiveOrder.remainedSize)) {
                    tradeSizeIceberg += passiveOrder.tradeSize;
                }
            }
        }
        if (tradeSizeIceberg > 0) {
            // TODO: update indicator's line;
        }

        if (this.stops.cache >= this.threshold) {
            var msg = 'Avalanche of Stops. ' + this.stops.cache + ' contracts within 10 milliseconds!';
            this.stops.clear();
            alertsListener.onAlert(msg);
        }
        if (this.icebergs.cache >= this.threshold) {
            var msg = this.icebergs.cache + ' Iceberg contracts within 10 milliseconds!';
            this.icebergs.clear();
            alertsListener.onAlert(msg);
        }
    }
}
