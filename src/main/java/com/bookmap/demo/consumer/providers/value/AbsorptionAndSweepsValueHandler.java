package com.bookmap.demo.consumer.providers.value;

import com.bookmap.addons.broadcasting.api.view.Event;
import com.bookmap.addons.broadcasting.api.view.EventFilter;
import com.bookmap.addons.broadcasting.implementations.base.CastUtilities;
import velox.api.layer1.data.InstrumentInfo;
import velox.indicators.absorption.broadcasting.module.EventInterface;
import velox.indicators.absorption.broadcasting.module.ProviderSettings;
import velox.indicators.absorption.broadcasting.module.implementations.Filter;
import velox.indicators.absorption.broadcasting.module.implementations.ProviderSettingsProxy;
import velox.indicators.absorption.broadcasting.module.implementations.TradeEvent;

import java.util.LinkedList;
import java.util.List;
import java.util.logging.Logger;

public class AbsorptionAndSweepsValueHandler implements ProviderValueHandler{
    private static final Logger LOGGER = Logger.getLogger(AbsorptionAndSweepsValueHandler.class.getName());

    @Override
    public String[] getTextualVisualizationOfEvent(Event event, InstrumentInfo instrumentInfo) {
        velox.indicators.absorption.broadcasting.module.EventInterface eventInterface =
                (EventInterface) event;

        double scale = Math.pow(10, 3);

        double price = eventInterface.getPrice() * instrumentInfo.pips;
        price = Math.ceil(price * scale) / scale;

        double size = eventInterface.getValue() / instrumentInfo.sizeMultiplier;
        size = Math.ceil(size * scale) / scale;

        double chainSize = eventInterface.getMaxChainSize() / instrumentInfo.sizeMultiplier;
        chainSize = Math.ceil(chainSize * scale) / scale;

        String firstRow = String.format("Price=%s, Size=%s, isBid=%s, Time=%s,",
                price, size, eventInterface.isBid(),
                ProviderValueHandler.convertTime(event.getTime()),
                chainSize);
        String secondRow = String.format(" ChainSize=%s;", chainSize);

        return new String[] {firstRow,secondRow};
    }

    @Override
    public String getGeneratorSettingsInfo(Object providerSettings) {
        ProviderSettings settings = (ProviderSettings) providerSettings;
        double scale = Math.pow(10, 3);
        double timeLimitMillis = settings.getTimeLimitMillis();
        timeLimitMillis = Math.ceil(timeLimitMillis * scale) / scale;
        double sizeLimit = settings.getSizeLimit();
        sizeLimit = Math.ceil(sizeLimit * scale) / scale;

        return "Generator information: Time limit - " + timeLimitMillis + ", size limit - "
                + sizeLimit;
    }

    @Override
    public Event castEventInOurClassLoader(Object o) {
        try {
            return CastUtilities.castObject(o, TradeEvent.class);
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast event to TradeEvent: " + t.getMessage());
            return null;
        }
    }

    @Override
    public List<Event> castEventsInOurClassLoader(List<Object> o) {
        try {
            return new LinkedList<>(CastUtilities.castObjects(o, TradeEvent.class));
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast events list to TradeEvent: " + t.getMessage());
            return new LinkedList<>();
        }
    }

    @Override
    public EventFilter<Event> castFilter(Object o) {
        try {
            return CastUtilities.castObject(o, Filter.class);
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast filter to Filter: " + t.getMessage());
            return null;
        }
    }

    @Override
    public Object castSettings(Object o) {
        try {
            return CastUtilities.castObject(o, ProviderSettingsProxy.class);
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast settings to ProviderSettingsProxy: " + t.getMessage());
            return null;
        }
    }
}
