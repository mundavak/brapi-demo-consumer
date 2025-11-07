package com.bookmap.demo.consumer.database;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Session Manager for generating and tracking trading sessions
 * Format: {symbol}_{yyyyMMdd_HHmmss}_{UUID}
 */
public class SessionManager {
    private static final SessionManager INSTANCE = new SessionManager();
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    private final Map<String, String> activeSessionsPerSymbol = new ConcurrentHashMap<>();

    private SessionManager() {
    }

    public static SessionManager getInstance() {
        return INSTANCE;
    }

    /**
     * Generate a new session ID for a symbol
     * 
     * @param symbol The trading symbol
     * @return Session ID in format: {symbol}_{yyyyMMdd_HHmmss}_{UUID}
     */
    public String generateSessionId(String symbol) {
        String timestamp = LocalDateTime.now().format(FORMATTER);
        String uuid = UUID.randomUUID().toString().substring(0, 8);
        String sessionId = String.format("%s_%s_%s", symbol, timestamp, uuid);

        activeSessionsPerSymbol.put(symbol, sessionId);
        return sessionId;
    }

    /**
     * Get the current session ID for a symbol
     * 
     * @param symbol The trading symbol
     * @return Current session ID or null if no active session
     */
    public String getCurrentSessionId(String symbol) {
        return activeSessionsPerSymbol.get(symbol);
    }

    /**
     * Clear session for a symbol
     * 
     * @param symbol The trading symbol
     */
    public void clearSession(String symbol) {
        activeSessionsPerSymbol.remove(symbol);
    }

    /**
     * Clear all sessions
     */
    public void clearAllSessions() {
        activeSessionsPerSymbol.clear();
    }
}
