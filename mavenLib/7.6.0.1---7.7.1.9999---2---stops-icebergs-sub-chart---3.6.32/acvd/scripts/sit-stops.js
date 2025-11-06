function(transaction, orderSizeFilter) {
    var size = transaction.aggressiveOrder.orderSize;
    return (transaction.aggressiveOrder.isStop && orderSizeFilter.accept(size))
        ? 0.0 + (transaction.aggressiveOrder.isBuy ? size : -size) : 0.0;
}
