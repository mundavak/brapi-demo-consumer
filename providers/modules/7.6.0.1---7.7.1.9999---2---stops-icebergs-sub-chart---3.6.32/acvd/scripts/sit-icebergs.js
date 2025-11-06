function(transaction, orderSizeFilter) {
    var size = 0;
    for each (var pa in transaction.passiveOrders) {
        if (pa.isNativeIceberg || pa.isCustomIceberg) {
            var orderSize = pa.lifetimeTradedSize + pa.remainedSize;
            if (orderSizeFilter.accept(orderSize)) {
                size += pa.tradeSize;
            }
        }
    }
    return 0.0 + (transaction.aggressiveOrder.isBuy ? -size : size);
}

return (transaction.aggressiveOrder.isBuy ? -1.0 : 1.0) * transaction.passiveOrders
    .filter(x => x.isNativeIceberg || x.isCustomIceberg).filter(x => orderSizeFilter.accept(x))
    .map(x => x.tradeSize).reduce((a, b) => a + b);
