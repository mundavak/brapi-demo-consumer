
// these objects are injected by the addon from Java
// aggressiveOrderSizeFilter, passiveOrderSizeFilter;
// var alertsListener;

function testAggr(order) {
    return order.isStop && aggressiveOrderSizeFilter.test(order.orderSize);
}
function testPass(order) {
    return order.isNativeIceberg && passiveOrderSizeFilter.test(order.lifetimeTradedSize + order.remainedSize);
}
var obj = {
    onTransaction: function(transaction) {
        if (testAggr(transaction.aggressiveOrder)) {
            var tradeSizeIceberg = 0;
            for each (var passiveOrder in transaction.passiveOrders) {
                if (testPass(passiveOrder)) {
                    tradeSizeIceberg += passiveOrder.tradeSize;
                }
            }
            if (tradeSizeIceberg > 0) {
                var priceSize = 0;
                for each (var passiveOrder in transaction.passiveOrders) {
                    if (testPass(passiveOrder)) {
                        priceSize += passiveOrder.tradeSize * passiveOrder.limitPrice;
                    }
                }
                var vwap = java.lang.Double.valueOf(priceSize / tradeSizeIceberg);
                alertsListener.onAlert(transaction.aggressiveOrder.timestamp, transaction.aggressiveOrder.isBuy, vwap, tradeSizeIceberg);
            }
        }
    }
}
