package com.bookmap.demo.consumer.utils;

import java.time.ZonedDateTime;
import java.time.ZoneId;
import java.time.LocalTime;
import java.util.Properties;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.logging.Logger;

/**
 * Utility class for CBDR (Central Bank Dealing Range) window detection
 * and session management
 */
public class SessionManager {
    private static final Logger LOGGER = Logger.getLogger(SessionManager.class.getName());
    private static SessionManager instance;

    private final ZoneId EST_ZONE = ZoneId.of("America/New_York");
    private Properties config;

    // CBDR Window times (EST)
    private LocalTime pmStart, pmEnd;
    private LocalTime londonStart, londonEnd;
    private LocalTime preNyStart, preNyEnd;
    private LocalTime tradingWindowStart, tradingWindowEnd;

    private SessionManager() {
        loadConfiguration();
    }

    public static synchronized SessionManager getInstance() {
        if (instance == null) {
            instance = new SessionManager();
        }
        return instance;
    }

    private void loadConfiguration() {
        config = new Properties();
        try {
            FileInputStream fis = new FileInputStream("F:/Databases/database_config.properties");
            config.load(fis);
            fis.close();

            // Parse CBDR window times
            pmStart = LocalTime.parse(config.getProperty("cbdr.pm.start", "16:00"));
            pmEnd = LocalTime.parse(config.getProperty("cbdr.pm.end", "20:00"));
            londonStart = LocalTime.parse(config.getProperty("cbdr.london.start", "02:00"));
            londonEnd = LocalTime.parse(config.getProperty("cbdr.london.end", "05:00"));
            preNyStart = LocalTime.parse(config.getProperty("cbdr.preny.start", "07:30"));
            preNyEnd = LocalTime.parse(config.getProperty("cbdr.preny.end", "09:30"));

            tradingWindowStart = LocalTime.parse(config.getProperty("trading.window.start", "08:00"));
            tradingWindowEnd = LocalTime.parse(config.getProperty("trading.window.end", "11:30"));

            LOGGER.info("Session configuration loaded successfully");
        } catch (IOException e) {
            LOGGER.severe("Failed to load configuration, using defaults: " + e.getMessage());
            setDefaults();
        }
    }

    private void setDefaults() {
        pmStart = LocalTime.of(16, 0);
        pmEnd = LocalTime.of(20, 0);
        londonStart = LocalTime.of(2, 0);
        londonEnd = LocalTime.of(5, 0);
        preNyStart = LocalTime.of(7, 30);
        preNyEnd = LocalTime.of(9, 30);
        tradingWindowStart = LocalTime.of(8, 0);
        tradingWindowEnd = LocalTime.of(11, 30);
    }

    /**
     * Determine which CBDR window the given timestamp falls into
     * @param timestamp Timestamp in milliseconds
     * @return CBDR window name (PM, LONDON, PRE_NY) or null if not in any window
     */
    public String getCbdrWindow(long timestamp) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(timestamp),
            EST_ZONE
        );
        LocalTime time = est.toLocalTime();

        if (isInWindow(time, pmStart, pmEnd)) {
            return "PM";
        } else if (isInWindow(time, londonStart, londonEnd)) {
            return "LONDON";
        } else if (isInWindow(time, preNyStart, preNyEnd)) {
            return "PRE_NY";
        }

        return null;
    }

    /**
     * Check if currently in a CBDR window
     */
    public boolean isInCbdrWindow() {
        return getCbdrWindow(System.currentTimeMillis()) != null;
    }

    /**
     * Check if currently in primary trading window (08:00-11:30 EST)
     */
    public boolean isInTradingWindow() {
        ZonedDateTime est = ZonedDateTime.now(EST_ZONE);
        LocalTime time = est.toLocalTime();
        return isInWindow(time, tradingWindowStart, tradingWindowEnd);
    }

    /**
     * Get current session type based on time
     */
    public String getSessionType(long timestamp) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(timestamp),
            EST_ZONE
        );
        LocalTime time = est.toLocalTime();

        // Asian session: 18:00 - 02:00 EST
        if (time.isAfter(LocalTime.of(18, 0)) || time.isBefore(LocalTime.of(2, 0))) {
            return "ASIAN";
        }
        // London session: 02:00 - 11:00 EST
        else if (time.isAfter(LocalTime.of(2, 0)) && time.isBefore(LocalTime.of(11, 0))) {
            return "LONDON";
        }
        // New York session: 08:00 - 17:00 EST (overlaps with London)
        else if (time.isAfter(LocalTime.of(8, 0)) && time.isBefore(LocalTime.of(17, 0))) {
            return "NEWYORK";
        }
        // After hours
        else {
            return "AFTER_HOURS";
        }
    }

    /**
     * Generate session ID based on date and session type
     */
    public String generateSessionId(String symbol) {
        ZonedDateTime est = ZonedDateTime.now(EST_ZONE);
        String sessionType = getSessionType(System.currentTimeMillis());
        return "%s_%s_%s".formatted(
                symbol,
                est.toLocalDate().toString().replace("-", ""),
                sessionType
        );
    }

    /**
     * Get session start time for a given timestamp
     */
    public long getSessionStartTime(long timestamp) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(timestamp),
            EST_ZONE
        );
        String sessionType = getSessionType(timestamp);

        switch (sessionType) {
            case "ASIAN":
                return est.with(LocalTime.of(18, 0)).toInstant().toEpochMilli();
            case "LONDON":
                return est.with(LocalTime.of(2, 0)).toInstant().toEpochMilli();
            case "NEWYORK":
                return est.with(LocalTime.of(8, 0)).toInstant().toEpochMilli();
            default:
                return est.with(LocalTime.of(17, 0)).toInstant().toEpochMilli();
        }
    }

    /**
     * Check if a time is within a window (handles overnight windows)
     */
    private boolean isInWindow(LocalTime time, LocalTime start, LocalTime end) {
        if (start.isBefore(end)) {
            // Normal window (e.g., 08:00 - 17:00)
            return !time.isBefore(start) && !time.isAfter(end);
        } else {
            // Overnight window (e.g., 18:00 - 02:00)
            return !time.isBefore(start) || !time.isAfter(end);
        }
    }

    /**
     * Get CBDR window start time
     */
    public long getCbdrWindowStart(String window, long referenceTime) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(referenceTime),
            EST_ZONE
        );

        LocalTime startTime;
        switch (window) {
            case "PM":
                startTime = pmStart;
                break;
            case "LONDON":
                startTime = londonStart;
                break;
            case "PRE_NY":
                startTime = preNyStart;
                break;
            default:
                return referenceTime;
        }

        return est.with(startTime).toInstant().toEpochMilli();
    }

    /**
     * Get CBDR window end time
     */
    public long getCbdrWindowEnd(String window, long referenceTime) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(referenceTime),
            EST_ZONE
        );

        LocalTime endTime;
        switch (window) {
            case "PM":
                endTime = pmEnd;
                break;
            case "LONDON":
                endTime = londonEnd;
                break;
            case "PRE_NY":
                endTime = preNyEnd;
                break;
            default:
                return referenceTime;
        }

        return est.with(endTime).toInstant().toEpochMilli();
    }

    /**
     * Convert timestamp to EST string
     */
    public String toEstString(long timestamp) {
        ZonedDateTime est = ZonedDateTime.ofInstant(
            java.time.Instant.ofEpochMilli(timestamp),
            EST_ZONE
        );
        return est.toString();
    }

    /**
     * Get current EST time
     */
    public ZonedDateTime getCurrentEst() {
        return ZonedDateTime.now(EST_ZONE);
    }

    /**
     * Check if it's a 24/7 operation time (always true for futures)
     */
    public boolean isOperational() {
        return true; // 24/7 for futures
    }

    /**
     * Get trading mode recommendation based on time and conditions
     */
    public String getRecommendedTradingMode() {
        if (isInTradingWindow()) {
            String cbdrWindow = getCbdrWindow(System.currentTimeMillis());
            if ("PRE_NY".equals(cbdrWindow)) {
                return "SCALPING"; // High volatility during pre-NY
            }
            return "INTRADAY"; // Main trading hours
        } else if (isInCbdrWindow()) {
            return "SESSION_TRADING"; // CBDR window opportunities
        } else {
            return "SWING_TRADING"; // Outside main hours
        }
    }
}

