
// these objects are injected by the addon from Java
// aggressiveOrdersSizeFilter, passiveOrdersSizeFilter;
// var alertsListener;

var obj = {
    onTransaction: function(transaction) {
        if (transaction.aggressiveOrder.isStop) {
            var tradeSizeIceberg = 0;
            for each (var passiveOrder in transaction.passiveOrders) {
                if (passiveOrder.isNativeIceberg) {
                    tradeSizeIceberg += passiveOrder.tradeSize;
                }
            }
            if (tradeSizeIceberg > 0) {
                //alertsListener.onAlert("3300.25");
                //alertsListener.onAlert('100', 'isBuy', '3300.25', '5');
                //alertsListener.onAlert(transaction.aggressiveOrder.timestamp, transaction.aggressiveOrder.isBuy, '3300.25', tradeSizeIceberg);
                alertsListener.onAlert(new java.lang.Double(transaction.aggressiveOrder.timestamp), transaction.aggressiveOrder.isBuy, new java.lang.Double(0.0), new java.lang.Double(tradeSizeIceberg));
            }
        }
    }
}
