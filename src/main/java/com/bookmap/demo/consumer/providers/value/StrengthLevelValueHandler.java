package com.bookmap.demo.consumer.providers.value;

import com.bookmap.addons.broadcasting.api.view.Event;
import com.bookmap.addons.broadcasting.api.view.EventFilter;
import com.bookmap.addons.broadcasting.implementations.base.CastUtilities;
import com.bookmap.addons.broadcasting.implementations.base.FailedToCastObject;
import com.bookmap.addons.strengthlevel.broadcasting.module.EventInterface;
import com.bookmap.addons.strengthlevel.broadcasting.module.ProviderSettings;
import com.bookmap.addons.strengthlevel.broadcasting.module.implementation.BrIcebergEvent;
import com.bookmap.addons.strengthlevel.broadcasting.module.implementation.Filter;
import com.bookmap.addons.strengthlevel.broadcasting.module.implementation.ProviderSettingsProxy;
import velox.api.layer1.data.InstrumentInfo;

import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class StrengthLevelValueHandler implements ProviderValueHandler {

    @Override
    public String[] getTextualVisualizationOfEvent(Event event, InstrumentInfo instrumentInfo) {
        EventInterface eventInterface = (EventInterface) event;

        String firstRow = "Price = %s, Size=%s, IsBid=%s, Time=%s,".formatted(
                eventInterface.getLevel(),
                eventInterface.getSize(),
                eventInterface.isBid(),
                ProviderValueHandler.convertTime(event.getTime())
        );
        return new String[] {firstRow};
    }

    @Override
    public String getGeneratorSettingsInfo(Object providerSettings) {
        ProviderSettings settings = (ProviderSettings) providerSettings;
        return "Settings: delay - " + TimeUnit.NANOSECONDS.toMillis(settings.getMaxPostTradeIncreaseDelay()) +
                ", minSize - " + settings.getMinPostTradeIncreaseSize();
    }

    @Override
    public Event castEventInOurClassLoader(Object o) {
        try {
            return CastUtilities.castObject(o, BrIcebergEvent.class);
        } catch (Throwable t) {
            return null;
        }
    }

    @Override
    public List<Event> castEventsInOurClassLoader(List<Object> o) {
        try {
            return new LinkedList<>(CastUtilities.castObjects(o, BrIcebergEvent.class));
        } catch (Throwable t) {
            return new LinkedList<>();
        }
    }

    @Override
    public EventFilter<Event> castFilter(Object o) {
        try {
            return CastUtilities.castObject(o, Filter.class);
        } catch (Throwable t) {
            return null;
        }
    }

    @Override
    public Object castSettings(Object o) {
        try {
            return CastUtilities.castObject(o, ProviderSettingsProxy.class);
        } catch (Throwable t) {
            return null;
        }
    }
}
