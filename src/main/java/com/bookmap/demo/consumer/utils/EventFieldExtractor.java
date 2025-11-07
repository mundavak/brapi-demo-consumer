package com.bookmap.demo.consumer.utils;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

/**
 * Utility class to extract ALL available fields from BrAPI events using
 * reflection.
 * This ensures we capture every piece of data the provider makes available.
 */
public class EventFieldExtractor {

    /**
     * Extract all fields and getter methods from an event object.
     * Returns a Map with field names as keys and their values.
     * 
     * @param event The event object to extract data from
     * @return Map of all field names → values
     */
    public static Map<String, Object> extractAllFields(Object event) {
        Map<String, Object> data = new HashMap<>();

        if (event == null) {
            return data;
        }

        // Extract direct fields
        extractFields(event, data);

        // Extract getter methods (may have additional computed values)
        extractGetters(event, data);

        return data;
    }

    /**
     * Extract all declared fields from the event object
     */
    private static void extractFields(Object event, Map<String, Object> data) {
        Field[] fields = event.getClass().getDeclaredFields();

        for (Field field : fields) {
            field.setAccessible(true);
            try {
                String fieldName = field.getName();
                Object value = field.get(event);

                // Store field value
                data.put(fieldName, value);

            } catch (Exception e) {
                // Field access failed - skip it
                data.put(field.getName(), null);
            }
        }
    }

    /**
     * Extract all public getter methods from the event object.
     * Getters may provide computed values not available as fields.
     */
    private static void extractGetters(Object event, Map<String, Object> data) {
        Method[] methods = event.getClass().getMethods();

        for (Method method : methods) {
            String methodName = method.getName();

            // Only process getter methods with no parameters
            if (!isGetter(methodName) || method.getParameterCount() != 0) {
                continue;
            }

            // Skip getClass()
            if (methodName.equals("getClass")) {
                continue;
            }

            try {
                Object value = method.invoke(event);

                // Convert getter name to field name (e.g., getValue → value, isActive → active)
                String fieldName = getterToFieldName(methodName);

                // Only store if not already captured from fields
                if (!data.containsKey(fieldName)) {
                    data.put(fieldName, value);
                }

            } catch (Exception e) {
                // Method invocation failed - skip it
            }
        }
    }

    /**
     * Check if a method name looks like a getter
     */
    private static boolean isGetter(String methodName) {
        return methodName.startsWith("get") || methodName.startsWith("is");
    }

    /**
     * Convert getter method name to field name
     * Examples: getValue → value, isActive → active, getOrderId → orderId
     */
    private static String getterToFieldName(String methodName) {
        String fieldName;

        if (methodName.startsWith("get")) {
            fieldName = methodName.substring(3); // Remove "get"
        } else if (methodName.startsWith("is")) {
            fieldName = methodName.substring(2); // Remove "is"
        } else {
            return methodName;
        }

        // Convert first character to lowercase
        if (fieldName.length() > 0) {
            fieldName = Character.toLowerCase(fieldName.charAt(0)) + fieldName.substring(1);
        }

        return fieldName;
    }

    /**
     * Get a specific field value with fallback to getter method
     */
    public static Object getFieldValue(Object obj, String fieldName) {
        if (obj == null) {
            return null;
        }

        // Try direct field access first
        try {
            Field field = obj.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            return field.get(obj);
        } catch (Exception e) {
            // Field not found, try getter methods
        }

        // Try getter method (getFieldName or isFieldName)
        try {
            String getter = "get" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
            Method method = obj.getClass().getMethod(getter);
            return method.invoke(obj);
        } catch (Exception e) {
            // Getter not found, try boolean getter
        }

        try {
            String getter = "is" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
            Method method = obj.getClass().getMethod(getter);
            return method.invoke(obj);
        } catch (Exception e) {
            // No getter found
            return null;
        }
    }

    /**
     * Convert a Map of extracted fields to JSON string
     */
    public static String toJsonString(Map<String, Object> data) {
        StringBuilder json = new StringBuilder("{");

        boolean first = true;
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            if (!first) {
                json.append(",");
            }
            first = false;

            json.append("\"").append(entry.getKey()).append("\":");

            Object value = entry.getValue();
            if (value == null) {
                json.append("null");
            } else if (value instanceof String) {
                json.append("\"").append(escape((String) value)).append("\"");
            } else if (value instanceof Number || value instanceof Boolean) {
                json.append(value);
            } else {
                // For complex objects, use toString()
                json.append("\"").append(escape(value.toString())).append("\"");
            }
        }

        json.append("}");
        return json.toString();
    }

    /**
     * Escape special characters for JSON
     */
    private static String escape(String str) {
        return str.replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }
}
