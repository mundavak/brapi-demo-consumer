package com.bookmap.demo.consumer.providers.value;

import com.bookmap.addons.broadcasting.api.view.Event;
import com.bookmap.addons.broadcasting.api.view.EventFilter;
import com.bookmap.addons.broadcasting.implementations.base.CastUtilities;
import velox.api.layer1.data.InstrumentInfo;

import java.lang.reflect.Method;
import java.util.LinkedList;
import java.util.List;
import java.util.logging.Logger;

/**
 * Value handler for Liquidity Markers indicator events
 * Uses reflection to handle events since we don't have direct access to the
 * event class
 */
public class LiquidityMarkersValueHandler implements ProviderValueHandler {
    private static final Logger LOGGER = Logger.getLogger(LiquidityMarkersValueHandler.class.getName());

    @Override
    public String[] getTextualVisualizationOfEvent(Event event, InstrumentInfo instrumentInfo) {
        try {
            // Use reflection to extract common fields
            double price = getDoubleField(event, "getPrice", "price") * instrumentInfo.pips;
            String levelType = getStringField(event, "getLevelType", "levelType", "UNKNOWN");
            double strength = getDoubleField(event, "getStrength", "strength");
            long volume = getLongField(event, "getVolume", "volume");

            String firstRow = "Price=%s, Type=%s, Strength=%.2f, Time=%s".formatted(
                    price, levelType, strength,
                    ProviderValueHandler.convertTime(event.getTime()));
            String secondRow = " Volume=%d".formatted(volume);

            return new String[] { firstRow, secondRow };
        } catch (Exception e) {
            LOGGER.warning("Failed to visualize liquidity event: " + e.getMessage());
            return new String[] { "Liquidity Level", "Time=" + ProviderValueHandler.convertTime(event.getTime()) };
        }
    }

    @Override
    public String getGeneratorSettingsInfo(Object providerSettings) {
        if (providerSettings == null) {
            return "Generator information: Default settings";
        }
        // Use reflection to get settings info
        try {
            String info = providerSettings.toString();
            return "Generator information: " + info;
        } catch (Exception e) {
            return "Generator information: Settings available";
        }
    }

    @Override
    public Event castEventInOurClassLoader(Object o) {
        try {
            // Try to cast as generic Event first
            if (o instanceof Event) {
                return (Event) o;
            }
            // If that fails, try reflection-based approach
            LOGGER.info("Attempting to cast liquidity event: " + o.getClass().getName());
            return null;
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast liquidity event: " + t.getMessage());
            return null;
        }
    }

    @Override
    public List<Event> castEventsInOurClassLoader(List<Object> o) {
        List<Event> events = new LinkedList<>();
        for (Object obj : o) {
            Event event = castEventInOurClassLoader(obj);
            if (event != null) {
                events.add(event);
            }
        }
        return events;
    }

    @Override
    public EventFilter<Event> castFilter(Object o) {
        try {
            return (EventFilter<Event>) o;
        } catch (Throwable t) {
            LOGGER.warning("Failed to cast filter: " + t.getMessage());
            return null;
        }
    }

    @Override
    public Object castSettings(Object o) {
        return o; // Return as-is, let Bookmap handle it
    }

    // Reflection helper methods
    private double getDoubleField(Object obj, String methodName, String fieldName) {
        try {
            Method method = obj.getClass().getMethod(methodName);
            Object result = method.invoke(obj);
            if (result instanceof Number) {
                return ((Number) result).doubleValue();
            }
        } catch (Exception e) {
            // Try field access
            try {
                java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                field.setAccessible(true);
                Object result = field.get(obj);
                if (result instanceof Number) {
                    return ((Number) result).doubleValue();
                }
            } catch (Exception ex) {
                // Ignore
            }
        }
        return 0.0;
    }

    private String getStringField(Object obj, String methodName, String fieldName, String defaultValue) {
        try {
            Method method = obj.getClass().getMethod(methodName);
            Object result = method.invoke(obj);
            return result != null ? result.toString() : defaultValue;
        } catch (Exception e) {
            try {
                java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                field.setAccessible(true);
                Object result = field.get(obj);
                return result != null ? result.toString() : defaultValue;
            } catch (Exception ex) {
                // Ignore
            }
        }
        return defaultValue;
    }

    private long getLongField(Object obj, String methodName, String fieldName) {
        try {
            Method method = obj.getClass().getMethod(methodName);
            Object result = method.invoke(obj);
            if (result instanceof Number) {
                return ((Number) result).longValue();
            }
        } catch (Exception e) {
            try {
                java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                field.setAccessible(true);
                Object result = field.get(obj);
                if (result instanceof Number) {
                    return ((Number) result).longValue();
                }
            } catch (Exception ex) {
                // Ignore
            }
        }
        return 0L;
    }
}
