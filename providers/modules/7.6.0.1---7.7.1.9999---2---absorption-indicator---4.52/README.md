# Absorption and Sweeps Indicators module for Broadcasting API.

This is a package of classes and interfaces needed to connect to 
Absorption and Sweeps Indicators as data providers using BrAPI.

Contains a class of events, filter, and provider settings.
After getting the objects of these classes through BrAPI, use CastUtilities from BrAPI to cast them.

TradeEvent as a trade event class has fields with price, size, time and bid or ask flag. But it also has maxChainSize - a field showing the size of the biggest bundle it is part of. The same event may be a part of multiple bundles at the same time, where each bundle includes all events within moving time window.  
For example, the user has specified some kind of time range. Three events were close enough to form a pack:  
Trade 1 with a size of 100.  
Trade 2 with a size of 100.  
Trade 3 with a size of 200.  
And also the user specified a minimum pack size of 300.  
The maxChainSize of this pack is 400. Therefore, we will take it into account and draw it.  
Then we will get these events from DataStructureInterface as follows:  
Trade 1 with a size of 100, maxChainSize - 400.  
Trade 2 with a size of 100, maxChainSize - 400.  
Trade 3 with a size of 200, maxChainSize - 400.  
However, when you get live events, you will see them like this:  
Trade 1 with a size of 100, maxChainSize- 100.  
Trade 2 with a size of 100, maxChainSize - 200.  
Trade 3 with a size of 200, maxChainSize- 400.  
If you need to track which trades were a part of absorption chain in live mode you will need to update maxChainSize value on the consumer side for all trades that were still in range of the moving time window (timeLimitMillis parameter) relative to the last trade you received for the instrument.